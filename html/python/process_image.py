import requests
import re
import logging

# List of romanian county codes for
# plate validation
counties = [ "B",
    "AB",
    "AG",
    "AR",
    "BC",
    "BH",
    "BN",
    "BR",
    "BT",
    "BV",
    "BZ",
    "CJ",
    "CL",
    "CS",
    "CT",
    "CV",
    "DB",
    "DJ",
    "GJ",
    "GL",
    "GR",
    "HD",
    "HR",
    "IF",
    "IL",
    "IS",
    "MH",
    "MM",
    "MS",
    "NT",
    "OT",
    "PH",
    "SB",
    "SJ",
    "SM",
    "SV",
    "TL",
    "TM",
    "TR",
    "VL",
    "VN",
    "VS",
]

# Function to validate a specific plate string
def is_valid_plate(plate):
    # Check if plate matches pattern [ X 00 XYZ ] or [ XY 000 XYZ ]
    template = "^([A-Z]|[a-z]){1,2}([0-9]){2,3}([A-Z]|[a-z]){3}$"

    match = re.search(template, plate)

    # Pattern for county codes: X/XX
    county_template = "^([A-Z]|[a-z]){1,2}"

    # Check general template match
    if match:
        # if the plate matches the whole pattern, check if the county code is valid
        county_match = re.search(county_template, plate)
        logging.info("\tPlate matches general pattern, checking county validity: '" + county_match.group(0).upper() + "'")
        # check if county exists in the 'counties' list
        if county_match.group(0).upper() in counties:
            logging.info("\tFound match, plate is valid")
            # plate matches pattern and county exists, so the plate
            # received as parameter is valid
            return True
        else:
            # plate's county doesn't exist in the counties list
            logging.info("\tInvalid county")
    else:
        # plate has an invalid format
        logging.info("\tPlate doesn't match general pattern")

    return False

# parse all the plates in the JSON received from the Plate Recognizer API
def parse_candidates(candidates):
    for candidate in candidates:
        plate = candidate['plate']
        logging.info("Checking candidate: '" + plate + "'")
        if is_valid_plate(plate):
            # check if the plate is vald
            # if yes, return the plate
            return True, plate
    logging.info("No valid candidate found, returning \"\"")
    # if no valid plate is found in the list of candidates, return an empty string
    return False, ""

# extract the data from the Plate Recognizer API
def extract_data_from_response(response):
    data = response.json()
    
    results = data['results']
    if len(results) < 1:
        return "N/A"
    map = results[0]
    plate = map['plate']

    # if no plate was found in the image
    # return an empty string
    if plate == "":
        return plate
    
    region_info = map['region']
    # extract the country code and precision score
    # from the response JSON
    region = region_info['code']
    region_score = region_info['score']

    candidates = map['candidates']

    # validate romanian plates
    # if the certainty of the region is higher than 70%
    # if not, just return the best match from the JSON
    if region == 'ro' and region_score > 0.7:
        logging.info("Checking plate: '" + plate + "'")
        # check the top match from the JSON
        if not is_valid_plate(plate):
            # if the top match is not a valid romanian plate,
            # parse the list of other candidates
            logging.info("Plate is not valid, checking other candidates...")
            found_valid, plate = parse_candidates(candidates)
            if not found_valid:
                plate = ""

    return plate

# function to send the image at imagePath
# to the Plate Recognizer API and extract the licence plate information from it
def parse_image(imagePath):
    plate = ""

    # Authorization token for the Plate Recognizer API POST request
    headers = {
    'Authorization': 'Token 2b207ee6b788bf0904351b831614f53ffb3dcfa1',
    }

    files = {
        'upload': (imagePath, open(imagePath, 'rb')),
        'regions': (None, 'us-ca'),
    }

    # Send image to API
    response = requests.post('https://api.platerecognizer.com/v1/plate-reader', headers=headers, files=files)
    logging.info("Received response from Plate Recognizer:")
    logging.info(response)

    # Extract the license plate from the JSON returned by the API
    plate = extract_data_from_response(response)

    return plate


# Function that checks if the image at path contains a license plate
def process(path):
    logging.info("Starting new image processing for image at path: '" + path + "'")

    # send the image to the API
    plate = parse_image(path)

    if plate != "":
        logging.info("Found plate: '" + plate + "'\n")
        return plate
    
    # if no plate is found or if the plates found are invalid
    # return 'N/A' as the image processing response
    logging.info("No plate was found\n")
    return "N/A"