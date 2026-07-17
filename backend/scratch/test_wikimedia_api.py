import asyncio
import httpx

async def main():
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": "binary search flowchart",
        "gsrnamespace": 6,  # File namespace
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "format": "json",
        "gsrlimit": 5,
    }
    headers = {
        "User-Agent": "NotesGeneratorApp/1.0 (prasanna@university.edu)"
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params, headers=headers)
        data = res.json()
        print("KEYS:", data.keys())
        if "query" in data:
            pages = data["query"]["pages"]
            print("PAGES COUNT:", len(pages))
            for page_id, info in pages.items():
                print(f"\n--- Page {page_id} ---")
                print("Title:", info.get("title"))
                imageinfo = info.get("imageinfo", [{}])[0]
                print("URL:", imageinfo.get("url"))
                print("Width:", imageinfo.get("width"))
                print("Height:", imageinfo.get("height"))
                extmetadata = imageinfo.get("extmetadata", {})
                license_name = extmetadata.get("LicenseShortName", {}).get("value")
                description = extmetadata.get("ImageDescription", {}).get("value")
                print("License:", license_name)
                print("Description length:", len(description) if description else 0)
        else:
            print("No query found in data:", data)

if __name__ == "__main__":
    asyncio.run(main())
