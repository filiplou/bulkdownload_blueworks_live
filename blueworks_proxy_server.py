"""
Proxy server for Blueworks Live API calls
Handles authentication and PDF downloads
"""

from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import requests
import json
import io
from datetime import datetime, timedelta
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load credentials
with open('bobAPIArtifactReporting.json', 'r') as f:
    auth_config = json.load(f)

CLIENT_ID = auth_config['client_id']
CLIENT_SECRET = auth_config['client_secret']
BASE_URL = 'https://ibm.blueworkslive.com'

# Token cache
access_token = None
token_expiry = None

def get_access_token():
    """Get or refresh OAuth access token"""
    global access_token, token_expiry
    
    # Check if we have a valid token
    if access_token and token_expiry and datetime.now() < token_expiry:
        return access_token
    
    print("Getting new access token...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            },
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            verify=False
        )
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        # Set expiry to 5 minutes before actual expiry
        token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
        
        print(f"[OK] Access token obtained (expires in {expires_in} seconds)")
        return access_token
        
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        raise

@app.route('/api/download-blueprint/<blueprint_id>')
def download_blueprint(blueprint_id):
    """Download blueprint as PDF"""
    try:
        # Get access token
        token = get_access_token()
        
        # Call Blueworks Live API
        api_url = f"{BASE_URL}/scr/api/PrintDiagram?processId={blueprint_id}"
        
        print(f"Downloading blueprint {blueprint_id}...")
        
        response = requests.get(
            api_url,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/pdf'
            },
            verify=False
        )
        
        if response.status_code != 200:
            print(f"[ERROR] API error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return jsonify({
                'error': f'API returned status {response.status_code}',
                'details': response.text[:200]
            }), response.status_code
        
        # Get blueprint name from query parameter
        blueprint_name = request.args.get('name', 'blueprint')
        filename = f"{blueprint_name.replace(' ', '_')}.pdf"
        
        print(f"[OK] Blueprint downloaded successfully")
        
        # Return PDF file
        return send_file(
            io.BytesIO(response.content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"[ERROR] Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-bpmn/<blueprint_id>', methods=['GET'])
def download_bpmn(blueprint_id):
    """Download blueprint as BPMN XML using export/process API"""
    try:
        # Get access token
        token = get_access_token()
        
        print(f"Step 1: Getting revision ID for process {blueprint_id}...")
        
        # Use the revision API to get all revisions
        # API format: /scr/api/revision/process/{processId}?showAll=true
        revision_url = f"{BASE_URL}/scr/api/revision/process/{blueprint_id}"
        
        revision_response = requests.get(
            revision_url,
            params={'showAll': 'true'},  # Get all revisions
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            },
            verify=False
        )
        
        if revision_response.status_code != 200:
            print(f"[ERROR] Failed to get revision ID: {revision_response.status_code}")
            print(f"Response: {revision_response.text[:500]}")
            return jsonify({
                'error': f'Failed to get revision ID. Status: {revision_response.status_code}',
                'details': revision_response.text[:500]
            }), revision_response.status_code
        
        revision_data = revision_response.json()
        print(f"Revision API response type: {type(revision_data)}")
        
        # The revision API returns a dict with 'tip' field containing the latest revision ID
        # Structure: {'tip': 'revision_id', 'revisions': [...], 'id': 'process_id', ...}
        revision_id = None
        
        if isinstance(revision_data, dict):
            # The 'tip' field contains the latest/current revision ID
            revision_id = revision_data.get('tip')
            
            if revision_id:
                print(f"Found tip (latest) revision ID: {revision_id}")
            else:
                # Fallback: try to get from revisions array
                revisions = revision_data.get('revisions', [])
                if revisions and len(revisions) > 0:
                    # Use the first revision in the array
                    revision_id = revisions[0].get('id')
                    print(f"Using first revision from array: {revision_id}")
                else:
                    print(f"[ERROR] No 'tip' field and no revisions array found")
                    print(f"Available keys: {list(revision_data.keys())}")
                    print(f"Response: {str(revision_data)[:500]}")
        
        elif isinstance(revision_data, list) and len(revision_data) > 0:
            # If it's an array, use the first revision
            revision_id = revision_data[0].get('id')
            print(f"Using first revision from list: {revision_id}")
        
        if not revision_id:
            print(f"[ERROR] Could not extract revision ID from response")
            return jsonify({
                'error': 'Could not determine revision ID',
                'details': 'Revision API response does not contain tip or revision ID',
                'response': str(revision_data)[:1000]
            }), 500
        
        print(f"Step 2: Using revision ID: {revision_id}")
        
        # Use the correct export/process API endpoint
        # Format: /scr/api/export/process/{processId}/{revisionId}
        api_url = f"{BASE_URL}/scr/api/export/process/{blueprint_id}/{revision_id}"
        
        print(f"Step 3: Downloading BPMN from {api_url}...")
        
        # Request BPMN export
        response = requests.get(
            api_url,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/xml, text/xml, */*'
            },
            verify=False
        )
        
        if response.status_code != 200:
            print(f"[ERROR] ExportProcess API error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return jsonify({
                'error': f'BPMN export failed. API returned status {response.status_code}',
                'details': response.text[:500] if response.text else 'No error details available',
                'suggestion': 'The BPMN export feature may not be enabled for this process or your account.'
            }), response.status_code
        
        # Get blueprint name from query parameter
        blueprint_name = request.args.get('name', 'blueprint')
        # Clean filename - remove special characters
        safe_name = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in blueprint_name)
        filename = f"{safe_name}.bpmn"
        
        print(f"[OK] BPMN downloaded successfully ({len(response.content)} bytes)")
        
        # Return BPMN XML file
        return send_file(
            io.BytesIO(response.content),
            mimetype='application/xml',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"[ERROR] Download error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Blueworks proxy server is running'})

if __name__ == '__main__':
    print("=" * 60)
    print("Blueworks Live Proxy Server")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Client ID: {CLIENT_ID}")
    print("Starting server on http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)

# Made with Bob
