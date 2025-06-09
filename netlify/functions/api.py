import magnum
from main import app  # Import your FastAPI app object

# Create the handler function that Netlify will use
handler = mangum.Mangum(app)