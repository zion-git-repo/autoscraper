from flask import Flask, render_template, jsonify, request, send_file, Response
import threading
import queue
import json
import os
from scraper import ClinicScraper

app = Flask(__name__)

# Global state
scraper_state = {
    'is_running': False,
    'scraper': None,
    'results': [],
    'thread': None
}

# Queue for sending progress updates to SSE clients
progress_queue = queue.Queue()


def scraper_callback(data):
    """Callback to receive updates from scraper"""
    # Put the data in queue for SSE clients
    progress_queue.put(data)


def run_scraper(sitemap_url, start_range, end_range, fields):
    """Run scraper in background thread"""
    scraper_state['is_running'] = True
    scraper_state['scraper'] = ClinicScraper(progress_callback=scraper_callback)

    try:
        results = scraper_state['scraper'].scrape(
            sitemap_url=sitemap_url,
            start_range=start_range,
            end_range=end_range,
            fields=fields
        )
        scraper_state['results'] = results

        # Save to CSV
        scraper_state['scraper'].save_to_csv(results)

        # Send completion event
        progress_queue.put({
            'type': 'complete',
            'total_results': len(results)
        })

    except Exception as e:
        progress_queue.put({
            'type': 'log',
            'level': 'error',
            'message': f'Fatal error: {str(e)}'
        })
    finally:
        scraper_state['is_running'] = False
        scraper_state['scraper'] = None


@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def start_scraping():
    """Start the scraping process"""
    if scraper_state['is_running']:
        return jsonify({'error': 'Scraper is already running'}), 400

    data = request.json
    start_range = data.get('start', 1)
    end_range = data.get('end', 10)
    fields = data.get('fields', ['name', 'address', 'phone', 'website'])

    # Validate range
    try:
        start_range = max(1, int(start_range))
        end_range = max(start_range, int(end_range))
    except (ValueError, TypeError):
        start_range = 1
        end_range = 10

    # Clear previous results
    scraper_state['results'] = []

    # Clear the queue
    while not progress_queue.empty():
        progress_queue.get()

    # Start scraper in background thread
    sitemap_url = 'https://www.hotdoc.com.au/sitemap.xml.gz'
    thread = threading.Thread(
        target=run_scraper,
        args=(sitemap_url, start_range, end_range, fields),
        daemon=True
    )
    scraper_state['thread'] = thread
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/stop', methods=['POST'])
def stop_scraping():
    """Stop the scraping process"""
    if not scraper_state['is_running']:
        return jsonify({'error': 'Scraper is not running'}), 400

    if scraper_state['scraper']:
        scraper_state['scraper'].stop()

    return jsonify({'status': 'stopping'})


@app.route('/api/status')
def get_status():
    """Get current scraper status"""
    return jsonify({
        'is_running': scraper_state['is_running'],
        'results_count': len(scraper_state['results'])
    })


@app.route('/api/results')
def get_results():
    """Get current results"""
    # Check if all results are requested
    all_results = request.args.get('all', 'false').lower() == 'true'

    if all_results:
        # Return all results for pagination
        return jsonify({
            'results': scraper_state['results'],
            'total': len(scraper_state['results'])
        })
    else:
        # Return first 10 for preview (legacy)
        return jsonify({
            'results': scraper_state['results'][:10],
            'total': len(scraper_state['results'])
        })


@app.route('/api/download')
def download_csv():
    """Download the results CSV"""
    csv_path = 'clinics.csv'

    if not os.path.exists(csv_path):
        return jsonify({'error': 'No CSV file available'}), 404

    return send_file(
        csv_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='clinics.csv'
    )


@app.route('/api/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"

        # Keep sending updates from the queue
        while True:
            try:
                # Wait for new data (with timeout to keep connection alive)
                data = progress_queue.get(timeout=30)
                yield f"data: {json.dumps(data)}\n\n"

                # If scraping is complete, we can continue listening for new jobs
                if data.get('type') == 'complete':
                    # Don't break, keep connection open for next scraping job
                    pass

            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f": heartbeat\n\n"
            except GeneratorExit:
                # Client disconnected
                break

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    print("🚀 Starting HotDoc Clinic Scraper...")
    print(f"📍 Open your browser to: http://localhost:{port}")
    if port == 5005:
        print("    (Note: Changed from port 5000 to 5005 due to macOS conflict)")
    app.run(debug=True, threaded=True, host='0.0.0.0', port=port)
