from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Fetch from the environment
SERP_API_KEY = os.getenv('SERP_API_KEY')
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', 8000)) 

# Pydantic model for the input data
class InstagramRequest(BaseModel):
    url: str

# Function to extract the Instagram post ID from the URL
def extract_instagram_id(url: str) -> str:
    try:
        # Split the URL to get the post ID
        return url.split("/p/")[1].split("/")[0]
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid Instagram URL format")

# Function to send a request to Instagram's GraphQL API to get the image
def sendRequestWithoutlogin(shortcode: str) -> str:
    instagram_url = "https://www.instagram.com/graphql/query"
    data = f"variables=%7B%22shortcode%22%3A%22{shortcode}%22%2C%22fetch_tagged_user_count%22%3Anull%2C%22hoisted_comment_id%22%3Anull%2C%22hoisted_reply_id%22%3Anull%7D&doc_id=8845758582119845"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(instagram_url, data=data, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error retrieving data from Instagram")
    
    try:
        return response.json()['data']['xdt_shortcode_media']['thumbnail_src']
    except KeyError:
        raise HTTPException(status_code=500, detail="Invalid response structure from Instagram")

# Function to filter visual matches based on price and stock availability
def filter_visual_matches(visual_matches):
    filtered_matches = []
    
    for match in visual_matches:
        # Check if both price object exists and in_stock is true
        if (
            'price' in match and 
            'in_stock' in match and 
            match['in_stock'] is True
        ):
            filtered_matches.append(match)
    
    return filtered_matches

# Async function to perform a Google Lens search using SerpAPI
async def google_lens_search(image_url: str):
    endpoint = "https://serpapi.com/search"
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": SERP_API_KEY
    }

    response = requests.get(endpoint, params=params)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error retrieving data from Google Lens API")
    
    result = response.json()
    
    # Filter the visual matches if they exist
    if 'visual_matches' in result:
        result['visual_matches'] = filter_visual_matches(result['visual_matches'])
    
    return result

# API route for processing the Instagram URL and performing the search
@app.post("/process_instagram_url")
async def process_instagram_url(request: InstagramRequest):
    # Step 1: Extract the Instagram post ID from the URL
    post_id = extract_instagram_id(request.url)
    
    # Step 2: Get the image URL from Instagram's GraphQL API
    image_url = sendRequestWithoutlogin(post_id)
    
    # Step 3: Perform a Google Lens search on the image and get filtered results
    google_lens_result = await google_lens_search(image_url)
    
    return {
        "google_lens_result": google_lens_result
    }

@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")  # Redirect to the FastAPI docs

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)