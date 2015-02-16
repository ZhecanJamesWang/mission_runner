#!/usr/bin/env python

import time
import json
import math
import os

import rospkg
import rospy
import rosbag
import roscopter
import roscopter.msg
import roscopter.srv
from std_srvs.srv import *
from sensor_msgs.msg import NavSatFix, NavSatStatus, Imu
from geodesy import utm


class QuadcopterBrain(object):
    '''
    High-level quadcopter controller.
    '''
    def __init__(self):
        self.clear_waypoints_service = rospy.ServiceProxy(
            'clear_waypoints', Empty)
        self.command_service = rospy.ServiceProxy(
            'command', roscopter.srv.APMCommand)
        self.waypoint_service = rospy.ServiceProxy(
            'waypoint', roscopter.srv.SendWaypoint)
        self.trigger_auto_service = rospy.ServiceProxy(
            'trigger_auto', Empty)
        self.adjust_throttle_service = rospy.ServiceProxy(
            'adjust_throttle', Empty)
        self.current_lat = 0.0
        self.current_long = 0.0
        self.current_rel_alt = 0.0
        self.current_alt = 0.0
        self.heading = 0.0
        rospy.Subscriber("/filtered_pos", roscopter.msg.FilteredPosition,
                         self.position_callback)
    
    def arm(self):
        self.command_service(roscopter.srv.APMCommandRequest.CMD_ARM)
        print('Armed')

    def launch(self):
        self.command_service(roscopter.srv.APMCommandRequest.CMD_LAUNCH)
        print('Launched')
        time.sleep(5)

    def go_to_waypoints(self, waypoint_data):
        waypoints = [build_waypoint(datum) for datum in waypoint_data]
        for waypoint in waypoints:
            self.send_waypoint(waypoint)

    def hover_in_place(self):
        # Test two options for stopping:
        # A - clear waypoints - does it then stop in place?
        self.clear_waypoints_service()
        print "Clearing waypoints... am I hovering in place?"
        # B - Send the quadcopter to a waypoint at its position
        # self.go_to_waypoints([{"latitude": self.current_lat,
        #                        "longitude": self.current_long,
        #                        "altitude": self.current_rel_alt}])

    def land(self):
        self.command_service(roscopter.srv.APMCommandRequest.CMD_LAND)
        print('Landing')

    def send_waypoint(self, waypoint):
        self.trigger_auto_service()
        self.adjust_throttle_service()
        successfully_sent_waypoint = False
        tries = 0
        while not successfully_sent_waypoint and tries < 5:
            res = self.waypoint_service(waypoint)
            successfully_sent_waypoint = res.result
            tries += 1
            if successfully_sent_waypoint:
                print('Sent waypoint %d, %d' % (waypoint.latitude,
                                                waypoint.longitude))

                # print self.check_reached_waypoint(waypoint)  # Uncomment after testing hover

                print "Waiting for 5 seconds until hover..."  # Remove after testing hover
                time.sleep(5.0)   # Remove after testing hover
                print "Hovering"   # Remove after testing hover
                self.hover_in_place()   # Remove after testing hover
                print "Waiting for 5 seconds until resuming..."  # Remove after testing hover
                time.sleep(5.0)   # Remove after testing hover
                print "Resuming"  # Remove after testing hover
            else:
                print("Failed to send waypoint %d, %d" % (waypoint.latitude,
                                                          waypoint.longitude))
                time.sleep(0.1)
                if tries == 5:
                    print("Tried %d times and giving up" % (tries))
                else:
                    print("Retrying. Tries: %d" % (tries))

    def check_reached_waypoint(self, waypoint):
        wait_time = 0
        while not self.has_reached_waypoint and wait_time < 50:
            time.sleep(5)
            wait_time += 5
            print "--> Traveling to waypoint for %d seconds" % (wait_time)
            print "--> Current position is %d, %d" % (self.current_lat,
                                                      self.current_long)
        if wait_time < 50:  # successfully reached
            time.sleep(5)  # stay at waypoint for a few seconds
            return "Reached waypoint"
        else:
            return "Failed to reach waypoint"

    def has_reached_waypoint(self, waypoint):
        latitude = mavlink_to_gps(waypoint.latitude)
        longitude = mavlink_to_gps(waypoint.longitude)
        error_margin = 3  # in meters
        try:
            _, _, dist_from_waypoint = \
                PositionTools.lat_lon_diff(self.current_lat,
                                           self.current_long,
                                           latitude,
                                           longitude)
            print "Distance to waypoint: " + str(dist_from_waypoint)
            print "Current lat: " + self.latitude + self.longitude
            return dist_from_waypoint < error_margin
        except AttributeError:  # if haven't gotten current position data
            return False

    def position_callback(self, data):
        self.current_lat = data.latitude
        self.current_long = data.longitude
        self.current_rel_alt = data.relative_altitude
        self.current_alt = data.altitude
        self.heading = data.heading

    def fly_path(self, waypoint_data):
        self.launch()
        self.go_to_waypoints(waypoint_data)
        self.land()


def build_waypoint(data):
    '''
    data: dictionary with latitude and longitude
          (altitude and hold_time optional)
    '''
    latitude = data['latitude']
    longitude = data['longitude']
    altitude = data.get('altitude', 8)
    hold_time = data.get('hold_time', 3.0)

    waypoint = roscopter.msg.Waypoint()
    waypoint.latitude = gps_to_mavlink(latitude)
    waypoint.longitude = gps_to_mavlink(longitude)
    waypoint.altitude = int(altitude * 1000)
    waypoint.hold_time = int(hold_time * 1000)  # in ms
    waypoint.waypoint_type = roscopter.msg.Waypoint.TYPE_NAV
    return waypoint


def gps_to_mavlink(coordinate):
    '''
    coordinate: decimal degrees
    '''
    return int(coordinate * 1e7)

def mavlink_to_gps(coordinate):
    '''
    coordinate: decimal degrees
    '''
    return int(coordinate / 1e7)


def open_waypoint_file(filename):
    f = open(filename)
    waypoints = json.load(f)
    rospack = rospkg.RosPack()
    quadcopter_brain_path = rospack.get_path("quadcopter_brain")
    source_path = "src"
    file_path = os.path.join(quadcopter_brain_path, source_path, filename)
    with open(file_path, "r") as f:
        waypoints = json.load(f)
    return waypoints


def main():
    rospy.init_node("quadcopter_brain")
    # In order to set the outside parameter, add _outside:=True to rosrun call
    outside = rospy.get_param("quadcopter_brain/outside", False)
    print "The code is in outside mode: ", outside
    carl = QuadcopterBrain()
    carl.clear_waypoints_service()
    print "Sleeping for 3 seconds..."
    rospy.sleep(3)
    great_lawn_waypoints = open_waypoint_file(
        "waypoint_data/great_lawn_waypoints.json")
    if outside:
        carl.arm()
    carl.fly_path([great_lawn_waypoints["A"], great_lawn_waypoints["B"]])


if __name__ == '__main__':
    main()
