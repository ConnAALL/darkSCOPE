# Check if argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 \"<google_drive_link>\""
    exit 1
fi

DRIVE_LINK="$1"

# Ensure gdown is installed
if ! command -v gdown &> /dev/null
then
    echo "gdown not found. Please install it using 'pip install gdown'"
    exit 1
fi

# Download file
gdown --fuzzy "$DRIVE_LINK"

if [ $? -eq 0 ]; then
    echo "Download completed successfully."
else
    echo "Download failed."
    exit 1
fi
