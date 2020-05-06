#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
# Snips RMV
# -----------------------------------------------------------------------------
# Copyright 2019 Patrick Fial
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import requests
import json
import logging
import time
from datetime import datetime, timedelta

from hss_skill import hss

# -----------------------------------------------------------------------------
# global definitions (RMV service endpoints)
# -----------------------------------------------------------------------------

LOCATION_SVC = "https://www.rmv.de/hapi/location.name"
TRIP_SVC = "https://www.rmv.de/hapi/trip"

SKILL_ID = "s710-rmv"

# -----------------------------------------------------------------------------
# class App
# -----------------------------------------------------------------------------

class App(hss.BaseSkill):

    # -------------------------------------------------------------------------
    # ctor

    def __init__(self):
        super().__init__()

        self.my_intents = ['s710:getTrainTo']

        self.logger = logging.getLogger(SKILL_ID)
        self.debug = debug

        # parameters

        self.mqtt_host = "localhost:1883"
        self.mqtt_user = None
        self.mqtt_pass = None

        self.rmv_api_key = None
        self.rmv_homestation = None
        self.rmv_homecity = None
        self.rmv_homecity_only = True
        self.time_offset = None
        self.short_info = False

        # get params from config.ini (HASS host + token)

        if 'rmv_api_key' in self.config['secret']:
            self.rmv_api_key = self.config['secret']['rmv_api_key']

        if 'rmv_homestation' in self.config['global']:
            self.rmv_homestation = self.config['global']['rmv_homestation']

        if 'rmv_homecity' in self.config['global']:
            self.rmv_homecity = self.config['global']['rmv_homecity']

        if 'rmv_homecity_only' in self.config['global'] and self.config['global']['rmv_homecity_only'] == "False":
            self.rmv_homecity_only = False

        if 'time_offset' in self.config['global']:
            self.time_offset = int(self.config['global']['time_offset'])

        if 'short_info' in self.config['global'] and self.config['global']['short_info'] == "True":
            self.short_info = True

        self.logger.debug("Connecting to {}@{} ...".format(self.mqtt_user, self.mqtt_host))

    # --------------------------------------------------------------------------
    # get_intentlist (overwrites BaseSkill.get_intentlist)
    # --------------------------------------------------------------------------

    def get_intentlist(self):
        return self.my_intents

    # --------------------------------------------------------------------------
    # handle (overwrites BaseSkill.handle)
    # --------------------------------------------------------------------------

    def handle(self, request, session_id, site_id, intent_name, slots):
        dep_time = slots["DepTime"] if "DepTime" in slots else None
        location = slots["Location"] if "Location" in slots else None

        if dep_time:
            dep_time = dep_time.split("+")[0].strip().split(" ")[-1]  # "2019-08-26 18:30:00 +00:00" -> "18:30:00"

    # -------------------------------------------------------------------------
    # on_intent

    def on_intent(self, hermes, intent_message):
        location = None
        dep_time = None

        # ignore unknown/unexpected intents

        if intent_name not in self.my_intents:
            self.log.warning("Ignoring unexpected/unknown intent {}".format(intent_name))
            return

        response_message = self.query(location, dep_time)

        return self.done(session_id, site_id, intent_name, response_message, "de_DE")

    # -------------------------------------------------------------------------
    # query

    def query(self, location, dep_time):
        tme = dep_time
        dest_id = None

        # origin-ID according to homecity config

        origin_id = self.get_location_id(self.rmv_homestation, self.rmv_homecity)

        # determine destination-ID according to supplied station

        if (self.rmv_homecity_only):
            dest_id = self.get_location_id(location, self.rmv_homecity)
        else:
            dest_id = self.get_location_id(location)

        if not origin_id or not dest_id:
            self.logger.error("Failed to determine stops")
            return False

        # set time to now + offset if no time given & we have offset in config

        if not tme and self.time_offset:
            dt = datetime.fromtimestamp(time.time()) + timedelta(minutes = self.time_offset)
            tme = dt.strftime("%H:%M:00")

        # get the trip

        stops = self.get_trip(origin_id, dest_id, tme)

        if stops is None:
            self.logger.error("Failed to query trip")
            return False

        response = self.make_response(stops)

        if self.debug:
            self.logger.debug("response:")
            self.logger.debug(response)
            self.logger.debug("query done.")

        return response

    # -------------------------------------------------------------------------
    # get_location_id

    def get_location_id(self, location_name, city = None):
        params = { "accessId": self.rmv_api_key, "type": "S", "format": "json", "maxNo": 1, "input": location_name }

        if (city is not None):
            params["input"] = location_name + " " + city

        r = requests.get(LOCATION_SVC, params = params)

        if r.status_code != 200 or not r.content:
            self.logger.error("Failed to determine location '{}' (HTTP {})".format(location_name, r.status_code))
            return None

        try:
            dict = json.loads(r.content.decode('utf-8'))
        except ValueError as e:
            self.logger.error("Failed to parse location query response ({})".format(e))
            return None
        except TypeError as e:
            self.logger.error("Failed to parse location query response ({})".format(e))
            return None
        except Exception as e:
            self.logger.error("Failed to parse location query response ({})".format(e))
            return None

        if "stopLocationOrCoordLocation" not in dict or not isinstance(dict["stopLocationOrCoordLocation"], list):
            return None

        if "StopLocation" not in dict["stopLocationOrCoordLocation"][0]:
            return None

        stop = dict["stopLocationOrCoordLocation"][0]["StopLocation"]

        return (stop["extId"], stop["name"])

    # -------------------------------------------------------------------------
    # get_trip

    def get_trip(self, origin_id, dest_id, time):
        params = { "accessId": self.rmv_api_key, "format": "json", "originExtId": origin_id[0], "destExtId": dest_id[0] }

        if time is not None:
            params["time"] = time

        r = requests.get(TRIP_SVC, params = params)

        if r.status_code != 200 or not r.content:
            self.logger.error("Failed to query trip from '{}' to '{}' (HTTP {})".format(origin_id[1], dest_id[1], r.status_code))
            return None

        try:
            dict = json.loads(r.content.decode('utf-8'))
        except ValueError as e:
            self.logger.error("Failed to parse trip query response ({})".format(e))
            return None
        except TypeError as e:
            self.logger.error("Failed to parse trip query response ({})".format(e))
            return None

        try:
            first_leg_list = dict["Trip"][0]["LegList"]["Leg"]
        except:
            self.logger.error("Unexpected response for trip query")
            return None

        return self.process_leg_list(first_leg_list)

    # -------------------------------------------------------------------------
    # process_leg_list

    def process_leg_list(self, leg_list):
        stops = []

        for leg in leg_list:
            try:
                stop = { "time": ":".join(leg["Origin"]["time"].split(":")[:2]), "arrival": ":".join(leg["Destination"]["time"].split(":")[:2]), "station": leg["Origin"]["name"], "dest_station": leg["Destination"]["name"] }

                if "direction" in leg:
                    stop["direction"] = leg["direction"]

                if "name" in leg:
                    stop["train"] = leg["name"].strip()

                if "Product" in leg and "catOutL" in leg["Product"]:
                    stop["category"] = leg["Product"]["catOutL"].strip()
                elif "type" in leg and leg["type"] == "WALK":
                    stop["category"] = "walk"

                if "dist" in leg:
                    stop["distance"] = str(leg["dist"])

                stops.append(stop)

            except KeyError as e:
                self.logger.error("Unexpected response contents for trip query (leg list) ({})".format(e))
                return None
            except:
                self.logger.error("Unexpected response contents for trip query (leg list)")
                return None

        return stops

    # -------------------------------------------------------------------------
    # make_response

    def make_response(self, stops):
        response_string = ""

        if not stops:
            return None

        for i in range(len(stops)):
            stop = stops[i]

            if stop["category"] == "walk":
                response_string += stop["distance"] + " Meter laufen bis " + stop["dest_station"] + ". "
            else:
                if i == 0:
                    response_string += self.get_train_title(stop["category"], stop["train"]) + " Richtung " + stop["direction"] + " um " + stop["time"] + " Uhr. "
                else:
                    response_string += "Umsteigen an " + stop["station"] +  " zu " + self.get_train_title(stop["category"], stop["train"]) + " Richtung " + stop["direction"] + " um " + stop["time"] + " Uhr. "

                if self.short_info:
                    break

        last = stops[-1]

        response_string += "Ankunft um " + last["arrival"] + " Uhr."
        return response_string

    # -------------------------------------------------------------------------
    # get_train_title

    def get_train_title(self, category, train):
        if category == "U-Bahn" or category == "S-Bahn":
            return category + " " + train

        return train

    # -------------------------------------------------------------------------
    # done

    def done(self, hermes, intent_message, response_message):
        if response_message is not None:
            hermes.publish_end_session(intent_message.session_id, response_message)
        else:
            hermes.publish_end_session(intent_message.session_id, "Verbindung konnte nicht abgefragt werden")

