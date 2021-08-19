# Needed to tell the flask server where to serve the dash app.
import dashinterface
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
