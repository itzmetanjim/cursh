"""Check the validity of apps in trusted.json by making HTTP requests to their URL patterns."""
import asyncio
import json
import aiohttp
import re
import time
from typing import List, Dict, Any


async def check_url(session: aiohttp.ClientSession, url: str, app_name: str, version: List[str] = None) -> Dict[str, Any]:
    """Check a single URL and return the result."""
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return {"success": True, "app_name": app_name, "version": version, "url": url}
            else:
                return {"success": False, "app_name": app_name, "version": version, "url": url, "status": response.status}
    except Exception as e:
        return {"success": False, "app_name": app_name, "version": version, "url": url, "error": str(e)}


async def process_app(session: aiohttp.ClientSession, app: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process a single app and return all URL check results."""
    results = []
    
    if len(app["valid_versions"]) == 0:
        # App with no specific versions
        url = app["url_pattern"].replace("\\/", "/").replace("\\.", ".").replace("\\\\", "\\")
        result = await check_url(session, url, app["name"])
        results.append(result)
    else:
        # App with specific versions
        for version in app["valid_versions"]:
            url_p = app["url_pattern"].replace("\\/", "/").replace("\\.", ".").replace("\\\\", "\\")
            # Replace capturing groups with corresponding values from version
            url = url_p
            for j, replacement in enumerate(version):
                url = re.sub(r'\([^)]*\)', replacement, url, count=1)
            
            result = await check_url(session, url, app["name"], version)
            results.append(result)
    
    return results


async def main():
    """Main async function to check all apps concurrently."""
    start_time = time.time()
    
    # Load trusted apps
    with open("trusted.json") as f:
        trusted = json.load(f)
    
    apps = trusted.get("apps", [])
    invalid_apps = set()  # Use set to avoid duplicates
    
    # Create aiohttp session with connection limits
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        print(f"Checking {len(apps)} apps...")
        
        # Create tasks for all apps
        tasks = [process_app(session, app) for app in apps]
        
        # Process apps in batches to avoid overwhelming servers
        batch_size = 20
        total_results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            # Flatten results and handle exceptions
            for app_results in batch_results:
                if isinstance(app_results, Exception):
                    print(f"ERROR: Batch processing failed: {app_results}")
                    continue
                
                total_results.extend(app_results)
            
            # Show progress
            progress = min(i + batch_size, len(tasks))
            print(f"Progress: {progress}/{len(tasks)} apps processed")
    
    # Process results
    for result in total_results:
        if not result["success"]:
            app_name = result["app_name"]
            version = result.get("version")
            url = result["url"]
            
            if "error" in result:
                if version:
                    print(f"ERROR App {app_name} with version {version} request failed: {result['error']}, url: {url}")
                else:
                    print(f"ERROR App {app_name} request failed: {result['error']}, url: {url}")
            else:
                if version:
                    print(f"WARN App {app_name} with version {version} is invalid (status: {result.get('status', 'unknown')})")
                else:
                    print(f"WARN App {app_name} is invalid (status: {result.get('status', 'unknown')})")
            
            invalid_apps.add(app_name)
    
    end_time = time.time()
    print(f"\nChecking completed in {end_time - start_time:.2f} seconds")
    
    # Report results
    if invalid_apps:
        print(f"\nInvalid apps ({len(invalid_apps)}):")
        for app_name in sorted(invalid_apps):
            print(f"- {app_name}")
    else:
        print("All apps are valid!")


if __name__ == "__main__":
    asyncio.run(main())