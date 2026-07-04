import os
import glob

frontend_dir = "/home/singh/programming/personalWebsite/subrato_portfolio_final/frontend"
html_files = glob.glob(os.path.join(frontend_dir, "*.html"))

for file in html_files:
    with open(file, 'r') as f:
        content = f.read()
        
    original = content
    
    # 1. Add config.js to head if not present
    if "config.js" not in content and "</head>" in content:
        content = content.replace("</head>", "    <script src=\"config.js\"></script>\n</head>")
        
    # 2. Remove const API_URL = 'http://localhost:8000';
    content = content.replace("const API_URL = 'http://localhost:8000';", "")
    
    if content != original:
        with open(file, 'w') as f:
            f.write(content)
        print(f"Updated {file}")
