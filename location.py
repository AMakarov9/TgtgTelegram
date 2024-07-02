from datetime import datetime
import pytz
import requests
import json
from urllib.parse import quote
import logging


logging.basicConfig()

current_datetime = datetime.now()
oslo_timezone = pytz.timezone('Europe/Oslo')
oslo_datetime = current_datetime.astimezone(oslo_timezone)
datetime_string = oslo_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

url = 'https://api.entur.io/journey-planner/v3/graphql'
headers = {
    'Content-Type': 'application/json',
    'ET-Client-Name': 'Sulten-student-ifi'
}


# https://api.entur.io/graphql-explorer/journey-planner-v3
# Bruker EnTur sin IDE for å lage queries.  


# Gets geo location
# https://developer.entur.org/pages-geocoder-intro

def _getRoutes(arrivalTime: str, startPoint: str, endPoint: str) -> dict: 

    '''
    Uses enTur journey-planner API to get route from startPoint to endPoint.
    The points should be either coordinates or NSR-id. 
    '''

    # arriveBy bestemmer om tiden beregnes med datetime som tid for ankomst eller tid for start. 
    logging.info("Entered getRoutes") 
    query = '''
        query ($to: Location!, $from: Location!, $numTripPatterns: Int, $dateTime: DateTime!){
        trip(
            from: $from
            to: $to
            numTripPatterns: $numTripPatterns
            dateTime: $dateTime
            walkSpeed: 1.3
            arriveBy: true
            ) {
                tripPatterns {
                expectedStartTime
                duration

                expectedEndTime
            }
        }
    }

'''

    startL = len(startPoint.split(","))
    endL = len(endPoint.split(","))
    if startL == 2 or endL == 2: 
        startPointList = startPoint.split(",")
        endPointList = endPoint.split(",")
       
        if startL == endL == 2: 
            data = {
                'query': query,
                'variables': {
                    "to": {"coordinates": {"latitude": float(endPointList[0]), "longitude": float(endPointList[1])}},
                    "from": {"coordinates": {"latitude": float(startPointList[0]), "longitude": float(startPointList[1])}}, 
                    "numTripPatterns": 1, 
                    "dateTime": arrivalTime
                }
            }
        elif startL > endL:
            data = {
                'query': query,
                'variables': {
                    "to": {"place": endPoint},
                    "from": {"coordinates": {"latitude": float(startPointList[0]), "longitude": float(startPointList[1])}}, 
                    "numTripPatterns": 1, 
                    "dateTime": arrivalTime
                }
            }
        else:
            data = {
                'query': query,
                'variables': {
                    "to": {"coordinates": {"latitude": float(endPointList[0]), "longitude": float(endPointList[1])}},
                    "from": {"place": startPoint}, 
                    "numTripPatterns": 1, 
                    "dateTime": arrivalTime
                }
            }
    else: 
        data = {
            'query': query,
            'variables': {
                "to": {"place": endPoint},
                "from": {"place": startPoint}, 
                "numTripPatterns": 1, 
                "dateTime": arrivalTime
            }
        }

    response = requests.post(url, headers=headers, data=json.dumps(data))
  
    if response.status_code == 200:
        logging.info('Received response')
        response_data = response.json()
        logging.info(response_data)
        return response_data
    else:
        print('Data not retrieved', response.status_code, response.text)
        return False

def _get_geolocation(adress: str) -> str:
    
    '''
        Returns a geolocation in the form of either coordinates or a NSR stopplace.  
    '''
    headersny ={'ET-Client-Name': 'Sulten-student-ifi'}
    # encoded_adress = quote(adress)
    geourl = f'https://api.entur.io/geocoder/v1/autocomplete?text={adress}&size=2&lang=no'
    try: 
        response = requests.get(geourl, headers=headersny)
        location = _parse_geolocation(response.json())
        return location
    except Exception as e:
        print(e)
        return False 

def _parse_geolocation(response: dict) -> str:
    
    '''
    Called by get_geolocation() and returns geolocation as either coordinate or NSR stopplace, after
    parsing response from entur API. 
    '''
    if type(response) != dict: 
        raise Exception("Argument is not dict")
       
    if len(response["features"]) == 0: 
        raise Exception("Response is empty, address is invalid.")
    
    else: 
        try: 
            test = response["features"][0]["properties"]["id"]
            
            # NSR stop place. 
            if test[0] == "N":
                return test
            
            # Address with coordinates
            else: 
                lat = response["features"][0]["geometry"]["coordinates"][1]
                long = response["features"][0]["geometry"]["coordinates"][0]
            
                return f"{lat},{long}"   
        except KeyError as e:
            print("Error: key not found in response", e) 
            return False
        except Exception as e: 
            print("Error: ", e)
            return False


def give_routes(arrivalTime: str, start: str, stopp: str) -> str: 
    print(arrivalTime, start, stopp)
    startAddresse = _get_geolocation(start)
    stoppAddresse = _get_geolocation(stopp)
    if startAddresse and stoppAddresse: 
        response = _getRoutes(arrivalTime, startAddresse, stoppAddresse)
        if response: 
            return _format_routes(response)
        else: 
            return False
    else: 
        return False


def _format_routes(data: dict) -> str:
    # print(data)
    formatted_routes = ""
    
    print(data)
    routes = data["data"]["trip"]["tripPatterns"]
    for pattern in routes:
        start_time = pattern["expectedStartTime"]
        end_time = pattern["expectedEndTime"]
        duration_sec = pattern["duration"]
        
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        
        start_time = start.strftime('%H:%M')
        end_time = end.strftime('%H:%M')


        # Convert duration from seconds to minutes
        duration_minutes = duration_sec // 60

        formatted_routes += f"If you start your journey at {start_time}, you will be there at {end_time}, it will take {duration_minutes} minutes.\n"

    return formatted_routes
