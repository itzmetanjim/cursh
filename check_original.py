"""Original synchronous version for performance comparison."""
import json
import requests
import re
import time

def main():
    start_time = time.time()
    
    with open("trusted.json") as f:
        trusted = json.load(f)
    apps=trusted.get("apps", [])
    invalid_apps=[]
    
    print(f"Checking {len(apps)} apps (synchronous)...")
    
    count = 0
    for app in apps:
        if len(app["valid_versions"]) == 0:
            url=app["url_pattern"].replace("\\/", "/").replace("\\.", ".").replace("\\\\","\\")
            try:
                r=requests.get(url, timeout=10)
            except requests.exceptions.RequestException as e:
                print(f"ERROR App {app['name']} request failed: {e}, url: {url}")
                invalid_apps.append(app)
                continue
            if r.status_code==200:
                pass
            else:
                print(f"WARN App {app['name']} is invalid")
                invalid_apps.append(app)
        else:
            for i in app["valid_versions"]:
                url_p=app["url_pattern"].replace("\\/", "/").replace("\\.", ".").replace("\\\\","\\")
                # Replace capturing groups with corresponding values from i
                url = url_p
                for j, replacement in enumerate(i):
                    url = re.sub(r'\([^)]*\)', replacement, url, count=1)
                try:
                    r=requests.get(url, timeout=10)
                except requests.exceptions.RequestException as e:
                    print(f"ERROR App {app['name']} with version {i} request failed: {e}, url: {url}")
                    if app not in invalid_apps:
                        invalid_apps.append(app)
                    continue
                if r.status_code==200:
                    pass
                else:
                    print(f"WARN App {app['name']} with version {i} is invalid")
                    if app not in invalid_apps:
                        invalid_apps.append(app)
        
        count += 1
        if count % 20 == 0:
            print(f"Progress: {count}/{len(apps)} apps processed")
    
    end_time = time.time()
    print(f"\nChecking completed in {end_time - start_time:.2f} seconds")
    
    if invalid_apps:
        print(f"\nInvalid apps ({len(invalid_apps)}):")
        for app in invalid_apps:
            print(f"- {app['name']}")
    else:
        print("All apps are valid!")

if __name__ == "__main__":
    main()