# Blueworks Live Bulk Export Tool

This project provides a web-based interface for viewing and bulk downloading Blueprint artifacts from IBM Blueworks Live.

## Files Included

### Core Application Files
- **blueworks_artifacts.html** - Main HTML page displaying first 100 artifacts with download capabilities
- **blueworks_proxy_server.py** - Flask proxy server handling OAuth authentication and API calls
- **user_analytics.html** - User analytics dashboard with charts and statistics
- **users_list.html** - List of all Blueworks Live users

### Data Files
- **blueworks_artifacts.csv** - CSV export of all Blueworks Live artifacts
- **active_users.json** - JSON file containing active user data
- **bobAPIArtifactReporting.json** - Authentication credentials for Blueworks Live API

### Generator Script
- **generate_simple_artifacts_viewer.py** - Python script to regenerate the artifacts HTML page

## Features

### Blueworks Artifacts Viewer
- ✅ Displays first 100 artifacts in a sortable table
- ✅ Individual PDF download buttons for each Blueprint
- ✅ Bulk download feature to download all Blueprints at once
- ✅ Color-coded artifact types (Blueprint, Space, Policy, Decision, Process App)
- ✅ Active/Inactive status indicators
- ✅ Cross-navigation to other pages

### User Analytics Dashboard
- ✅ Total users and growth metrics
- ✅ Monthly registration trends
- ✅ Day of week analysis
- ✅ User roles distribution
- ✅ Cumulative growth chart
- ✅ Daily activity (last 90 days)
- ✅ License status breakdown

## Setup Instructions

High level steps:

1: generate your own API keys from the www.blueworkslive.com website and put the .json files in the project folder. 

2: update the blueworks_api_client.py and blueworks_proxy_server.py with the correct API key .json file names and base URL, e.g. https://mcb.blueworkslive.com

3: start the proxy server to enable downloading. e.g. 
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:/bob/blueworkslive/bulk export' ; python blueworks_proxy_server.py"

4: open the blueworks_artifacts.html page to view the first 100 processes and download them.



### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. Install required Python packages:
```bash
pip install flask flask-cors requests
```

2. Ensure all files are in the same directory

### Running the Application

1. **Start the proxy server** (required for PDF downloads):
```bash
python blueworks_proxy_server.py
```
The server will start on http://localhost:5000

2. **Open the HTML pages** in your web browser:
   - `blueworks_artifacts.html` - Main artifacts viewer
   - `user_analytics.html` - Analytics dashboard
   - `users_list.html` - Users list

## Usage

### Viewing Artifacts
1. Open `blueworks_artifacts.html` in your browser
2. Browse through the first 100 artifacts
3. Use the navigation buttons to switch between pages

### Downloading Individual Blueprints
1. Click the "📥 PDF" button next to any Blueprint artifact
2. The PDF will be downloaded automatically
3. The button shows loading state during download

### Bulk Downloading Blueprints
1. Click the red "📥 Bulk Download All Blueprints" button at the top
2. Confirm the download in the popup dialog
3. All Blueprint PDFs will be downloaded sequentially
4. Progress is shown on the button
5. A summary is displayed when complete

### Viewing Analytics
1. Open `user_analytics.html` in your browser
2. View various charts and statistics
3. Use the time range selector to filter data
4. Navigate to other pages using the top navigation bar

## Authentication

The application uses OAuth 2.0 authentication with IBM Blueworks Live:
- **Client ID**: Stored in `bobAPIArtifactReporting.json`
- **Client Secret**: Stored in `bobAPIArtifactReporting.json`
- **Token Management**: Automatic token refresh handled by proxy server

## API Endpoints

The proxy server provides the following endpoint:
- `GET /api/download-blueprint/<blueprint_id>?name=<blueprint_name>` - Download a blueprint as PDF

## Technical Details

### Architecture
- **Frontend**: HTML/CSS/JavaScript with Chart.js for visualizations
- **Backend**: Flask proxy server to handle CORS and authentication
- **API**: IBM Blueworks Live REST API

### Authentication Flow
1. Proxy server obtains OAuth access token using client credentials
2. Token is cached and automatically refreshed before expiry
3. All API calls include Bearer token in Authorization header

### CORS Handling
- Direct browser calls to Blueworks Live API are blocked by CORS
- Proxy server acts as intermediary to bypass CORS restrictions
- All API calls go through http://localhost:5000

## Troubleshooting

### Downloads Not Working
- Ensure the proxy server is running (`python blueworks_proxy_server.py`)
- Check that port 5000 is not blocked by firewall
- Verify authentication credentials in `bobAPIArtifactReporting.json`

### Charts Not Displaying
- Ensure internet connection (Chart.js loads from CDN)
- Check browser console for JavaScript errors
- Refresh the page

### Empty Data
- Verify `blueworks_artifacts.csv` and `active_users.json` contain data
- Check file paths are correct
- Ensure files are in the same directory as HTML files

## Regenerating the Artifacts Page

If you need to update the artifacts page with new data:

1. Update `blueworks_artifacts.csv` with latest data
2. Run the generator script:
```bash
python generate_simple_artifacts_viewer.py
```
3. Refresh `blueworks_artifacts.html` in your browser

## Notes

- The artifacts viewer shows the first 100 results only
- Bulk download processes one Blueprint at a time with 500ms delay
- All downloads are saved to your browser's default download location
- PDF filenames are sanitized (special characters replaced with underscores)

## Support

For issues or questions, refer to the IBM Blueworks Live documentation:
https://www.ibm.com/docs/en/blueworks-live

## Version

Created: March 2026

Last Updated: March 9, 2026
