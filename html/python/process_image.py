import json
import requests
#import json
import re
import logging

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

def is_valid_plate(plate):
    template = "^([A-Z]|[a-z]){1,2}([0-9]){2,3}([A-Z]|[a-z]){3}$"

    match = re.search(template, plate)

    county_template = "^([A-Z]|[a-z]){1,2}"

    if match:
        county_match = re.search(county_template, plate)
        logging.info("\tPlate matches general pattern, checking county validity: '" + county_match.group(0).upper() + "'")
        if county_match.group(0).upper() in counties:
            logging.info("\tFound match, plate is valid")
            return True
        else:
            logging.info("\tInvalid county")
    else:
        logging.info("\tPlate doesn't match general pattern")

    return False

def parse_candidates(candidates):
    for candidate in candidates:
        plate = candidate['plate']
        logging.info("Checking candidate: '" + plate + "'")
        if is_valid_plate(plate):
            return True, plate
    logging.info("No valid candidate found, returning \"\"")
    return False, ""

def extract_data_from_response(response):
    data = response.json()
    
    results = data['results']
    map = results[0]
    plate = map['plate']

    if plate == "":
        return plate
    
    region_info = map['region']
    region = region_info['code']
    region_score = region_info['score']

    candidates = map['candidates']

    # Validate romanian plates
    if region == 'ro' and region_score > 0.7:
        logging.info("Checking plate: '" + plate + "'")
        if not is_valid_plate(plate):
            logging.info("Plate is not valid, checking other candidates...")
            found_valid, plate = parse_candidates(candidates)
            if not found_valid:
                plate = ""
    return plate

def parse_image(imagePath):
    plate = ""

    headers = {
    'Authorization': 'Token 2b207ee6b788bf0904351b831614f53ffb3dcfa1',
}

    files = {
        'upload': (imagePath, open(imagePath, 'rb')),
        'regions': (None, 'us-ca'),
    }

    # Use API
    response = requests.post('https://api.platerecognizer.com/v1/plate-reader', headers=headers, files=files)
    logging.info("Received response from Plate Recognizer:")
    logging.info(response)
    plate = extract_data_from_response(response)

    # plate = "TEST"
    return plate


def process(path):
    logging.info("Starting new image processing for image at path: '" + path + "'")
    plate = parse_image(path)

    if plate != "":
        logging.info("Found plate: '" + plate + "'\n")
        return plate
    
    logging.info("No plate was found\n")
    return ""