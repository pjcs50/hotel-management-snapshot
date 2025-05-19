"""
Simple script to test login functionality via requests.
"""

import requests
from bs4 import BeautifulSoup

# URL for login page
login_url = 'http://127.0.0.1:5000/auth/login'

# Test credentials from sample_data.py
username = 'admin@example.com'
password = 'password'

def test_login():
    """Test login functionality using requests."""
    # First, get the login page to retrieve CSRF token
    session = requests.Session()
    response = session.get(login_url)
    
    if response.status_code != 200:
        print(f"Failed to access login page: {response.status_code}")
        print(response.text)
        return
    
    # Parse the login page HTML to extract CSRF token
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = None
    
    # Look for CSRF token in a hidden input field
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if csrf_input:
        csrf_token = csrf_input.get('value')
    
    if not csrf_token:
        print("Could not find CSRF token in login page")
        return
    
    # Prepare login data
    login_data = {
        'email': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    # Submit login request
    login_response = session.post(login_url, data=login_data)
    
    if login_response.status_code == 200:
        print("Login response received with status 200")
        if "Invalid email or password" in login_response.text:
            print("Login failed: Invalid credentials")
        else:
            print("Login may have succeeded")
    else:
        print(f"Login failed with status code: {login_response.status_code}")
    
    print(f"Response redirect URL: {login_response.url}")
    
    # Attempt to access protected page
    dashboard = session.get('http://127.0.0.1:5000/')
    print(f"Dashboard access status: {dashboard.status_code}")
    print(f"Dashboard URL after redirect: {dashboard.url}")

if __name__ == '__main__':
    test_login() 