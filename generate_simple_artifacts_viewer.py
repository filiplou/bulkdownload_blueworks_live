import csv
import html
import json

def generate_simple_html():
    # Read authentication credentials
    with open('bobAPIArtifactReporting.json', 'r') as f:
        auth_config = json.load(f)
    
    client_id = auth_config.get('client_id', '')
    client_secret = auth_config.get('client_secret', '')
    """Generate a single HTML page with first 100 artifacts"""
    
    # Read first 100 artifacts from CSV
    artifacts = []
    with open('blueworks_artifacts.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= 100:
                break
            artifacts.append(row)
    
    total_count = 14065  # Total from previous run
    
    # Start HTML
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blueworks Artifacts - First 100 Results</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        .header .stats { font-size: 1.1em; opacity: 0.9; }
        .navigation { background: #f8f9fa; padding: 20px 30px; border-bottom: 2px solid #e9ecef; display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; }
        .quick-link { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1em; font-weight: 600; transition: all 0.3s ease; text-decoration: none; display: inline-block; }
        .quick-link:hover { background: #218838; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(40, 167, 69, 0.4); }
        .table-container { overflow-x: auto; padding: 30px; }
        table { width: 100%; border-collapse: collapse; font-size: 0.95em; }
        thead { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; position: sticky; top: 0; z-index: 10; }
        th { padding: 15px 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.85em; letter-spacing: 0.5px; }
        td { padding: 12px; border-bottom: 1px solid #e9ecef; vertical-align: middle; }
        .download-btn { padding: 6px 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 600; transition: all 0.2s ease; text-decoration: none; display: inline-block; margin-right: 5px; }
        .download-btn:hover { background: #0056b3; transform: scale(1.05); }
        .download-btn:disabled { background: #6c757d; cursor: not-allowed; opacity: 0.5; }
        .download-btn.bpmn { background: #17a2b8; }
        .download-btn.bpmn:hover { background: #138496; }
        tbody tr { transition: background-color 0.2s ease; }
        tbody tr:hover { background-color: #f8f9fa; }
        tbody tr:nth-child(even) { background-color: #f8f9fa; }
        tbody tr:nth-child(even):hover { background-color: #e9ecef; }
        .type-badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600; text-transform: uppercase; }
        .type-blueprint { background: #e3f2fd; color: #1976d2; }
        .type-space { background: #f3e5f5; color: #7b1fa2; }
        .type-policy { background: #fff3e0; color: #f57c00; }
        .type-decision { background: #e8f5e9; color: #388e3c; }
        .type-processapp { background: #fce4ec; color: #c2185b; }
        .status-active { color: #28a745; font-weight: 600; }
        .status-inactive { color: #dc3545; font-weight: 600; }
        .footer { background: #f8f9fa; padding: 20px 30px; text-align: center; color: #6c757d; border-top: 2px solid #e9ecef; }
        @media (max-width: 768px) {
            .header h1 { font-size: 1.8em; }
            table { font-size: 0.85em; }
            th, td { padding: 8px 6px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔷 Blueworks Artifacts Viewer</h1>
            <div class="stats">Displaying First 100 of """ + f"{total_count:,}" + """ Total Artifacts</div>
        </div>
        <div class="navigation">
            <button id="bulkDownloadBtn" class="quick-link" style="background: #dc3545;" onclick="bulkDownloadBlueprints()">📥 Bulk Download All Blueprints</button>
            <a href="blueworks_artifacts.html" class="quick-link" style="background: #6c757d;">📦 Artifacts</a>
            <a href="user_analytics.html" class="quick-link">📊 User Analytics</a>
            <a href="users_list.html" class="quick-link">👥 Users List</a>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Action</th>
                        <th>#</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Space Name</th>
                        <th>Status</th>
                        <th>Created By</th>
                        <th>Created Date</th>
                        <th>Last Modified</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add rows
    for idx, artifact in enumerate(artifacts, 1):
        artifact_type = artifact.get('Type', '').lower().replace(' ', '')
        type_class = f"type-{artifact_type}" if artifact_type else "type-blueprint"
        
        is_active = artifact.get('Is Active', '').lower() == 'true'
        status_class = 'status-active' if is_active else 'status-inactive'
        status_text = '✓ Active' if is_active else '✗ Inactive'
        
        # Add download buttons only for blueprints
        artifact_id = artifact.get('ID', '')
        artifact_name = artifact.get('Name', 'artifact')
        download_cell = ''
        if artifact.get('Type', '').lower() == 'blueprint' and artifact_id:
            download_cell = f'<button class="download-btn" onclick="downloadBlueprint(\'{artifact_id}\', \'{html.escape(artifact_name, quote=True)}\')">📥 PDF</button>'
            download_cell += f'<button class="download-btn bpmn" onclick="downloadBPMN(\'{artifact_id}\', \'{html.escape(artifact_name, quote=True)}\')">📊 BPMN</button>'
        
        html_content += f"""                    <tr>
                        <td>{download_cell}</td>
                        <td>{idx}</td>
                        <td><strong>{html.escape(artifact.get('Name', 'N/A'))}</strong></td>
                        <td><span class="type-badge {type_class}">{html.escape(artifact.get('Type', 'N/A'))}</span></td>
                        <td>{html.escape(artifact.get('Space Name', 'N/A'))}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{html.escape(artifact.get('Created By User', 'N/A'))}</td>
                        <td>{html.escape(artifact.get('Created Date', 'N/A'))}</td>
                        <td>{html.escape(artifact.get('Last Modified Date', 'N/A'))}</td>
                    </tr>
"""
    
    html_content += f"""                </tbody>
            </table>
        </div>
        <div class="footer">
            <p>Generated from blueworks_artifacts.csv | Showing First 100 Records</p>
            <p style="margin-top: 10px; font-size: 0.9em; color: #dc3545;">
                <strong>Note:</strong> Make sure the proxy server is running: <code>python blueworks_proxy_server.py</code>
            </p>
        </div>
    </div>
    <script>
        // Use local proxy server to avoid CORS issues
        const PROXY_URL = 'http://localhost:5000';
        
        async function downloadBlueprint(blueprintId, blueprintName) {{
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '⏳ Loading...';
            
            try {{
                // Call local proxy server
                const apiUrl = PROXY_URL + '/api/download-blueprint/' + blueprintId + '?name=' + encodeURIComponent(blueprintName);
                
                const response = await fetch(apiUrl);
                
                if (!response.ok) {{
                    throw new Error('HTTP error! status: ' + response.status);
                }}
                
                // Get the PDF blob
                const blob = await response.blob();
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = blueprintName.replace(/[^a-z0-9]/gi, '_') + '.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                btn.disabled = false;
                btn.textContent = '📥 PDF';
                
            }} catch (error) {{
                console.error('Download error:', error);
                alert('Failed to download blueprint: ' + error.message);
                btn.disabled = false;
                btn.textContent = '📥 PDF';
            }}
        }}
        
        async function downloadBPMN(blueprintId, blueprintName) {{
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '⏳ Loading...';
            
            try {{
                // Call local proxy server for BPMN export
                const apiUrl = PROXY_URL + '/api/download-bpmn/' + blueprintId + '?name=' + encodeURIComponent(blueprintName);
                
                const response = await fetch(apiUrl);
                
                if (!response.ok) {{
                    throw new Error('HTTP error! status: ' + response.status);
                }}
                
                // Get the BPMN XML blob
                const blob = await response.blob();
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = blueprintName.replace(/[^a-z0-9]/gi, '_') + '.bpmn';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                btn.disabled = false;
                btn.textContent = '📊 BPMN';
                
            }} catch (error) {{
                console.error('Download error:', error);
                alert('Failed to download BPMN: ' + error.message);
                btn.disabled = false;
                btn.textContent = '📊 BPMN';
            }}
        }}
        
        async function bulkDownloadBlueprints() {{
            const bulkBtn = document.getElementById('bulkDownloadBtn');
            const downloadButtons = document.querySelectorAll('.download-btn');
            
            if (downloadButtons.length === 0) {{
                alert('No blueprints found on this page to download.');
                return;
            }}
            
            const confirmed = confirm(`This will download ${{downloadButtons.length}} blueprints. Continue?`);
            if (!confirmed) return;
            
            bulkBtn.disabled = true;
            bulkBtn.textContent = '⏳ Downloading 0/' + downloadButtons.length;
            
            let completed = 0;
            let failed = 0;
            
            // Download with delay to avoid overwhelming the server
            for (let i = 0; i < downloadButtons.length; i++) {{
                const btn = downloadButtons[i];
                const blueprintId = btn.getAttribute('onclick').match(/'([^']+)'/)[1];
                const blueprintName = btn.getAttribute('onclick').match(/'([^']+)', '([^']+)'/)[2];
                
                try {{
                    bulkBtn.textContent = `⏳ Downloading ${{completed + 1}}/${{downloadButtons.length}}`;
                    
                    const apiUrl = PROXY_URL + '/api/download-blueprint/' + blueprintId + '?name=' + encodeURIComponent(blueprintName);
                    const response = await fetch(apiUrl);
                    
                    if (!response.ok) {{
                        throw new Error('HTTP error! status: ' + response.status);
                    }}
                    
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = blueprintName.replace(/[^a-z0-9]/gi, '_') + '.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    completed++;
                    
                    // Small delay between downloads
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                }} catch (error) {{
                    console.error(`Failed to download ${{blueprintName}}:`, error);
                    failed++;
                }}
            }}
            
            bulkBtn.disabled = false;
            bulkBtn.textContent = '📥 Bulk Download All Blueprints';
            
            if (failed > 0) {{
                alert(`Bulk download complete!\\n\\nSuccessful: ${{completed}}\\nFailed: ${{failed}}`);
            }} else {{
                alert(`Successfully downloaded all ${{completed}} blueprints!`);
            }}
        }}
    </script>
</body>
</html>
"""
    
    # Write file
    with open('blueworks_artifacts.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[OK] Generated blueworks_artifacts.html")
    print(f"  - Displaying first 100 of {total_count:,} total artifacts")

if __name__ == "__main__":
    generate_simple_html()

# Made with Bob
