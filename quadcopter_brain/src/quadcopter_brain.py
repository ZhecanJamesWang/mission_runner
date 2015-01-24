#!/usr/bin/env python

import rospy
import time
import json
import math

import roscopter
import roscopter.msg
import roscopter.srv
from std_srvs.srv import *
from sensor_msgs.msg import NavSatFix, NavSatStatus, Imu


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
        # self.land_service = rospy.ServiceProxy(
        #     'land', Empty
        # )
        
    def send_waypoint(self, waypoint):
        successfully_sent_waypoint = False
        tries = 0

        while not successfully_sent_waypoint and tries < 5:
            res = self.waypoint_service(waypoint)
            successfully_sent_waypoint = res.result
            tries += 1
            if successfully_sent_waypoint:
                print('Sent waypoint %d, %d' % (waypoint.latitude,
                                                waypoint.longitude))
                print self.check_reached_waypoint(waypoint):
            else:
                print("Failed to send waypoint %d, %d" % (waypoint.latitude,
                                                          waypoint.longitude))
                time.sleep(0.1)
                if tries == 5:
                    print("Tried % times and giving up" % (tries)) 
                else:
                    print("Trying again. Tries: %d" % (tries))

    def check_reached_waypoint(self, waypoint):
        wait_time = 0
        rospy.Subscriber("/filtered_pos", roscopter.msg.FilteredPosition,
                         self.position_callback) 
        time.sleep(5)
        wait_time += 5
        print "Traveling to waypoint for %d seconds" % (wait_time)
        print "Current position is %d, %d" % (self.current_lat,
                                              self.current_long)
        if not self.has_reached_waypoint(waypoint):
            rospy.spin()
        return "Reached waypoint"

    def has_reached_waypoint(self, waypoint):
        print("In reached waypoint")
        try:
            lat_delta = math.fabs(self.current_lat - waypoint.latitude) 
            long_delta = math.fabs(self.current_long - waypoint.longitude)
            return lat_delta < 30 and long_delta < 30
        except:
            return False

    def position_callback(self, data):
        print "Updating Position Data"
        self.current_lat = data.latitude
        self.current_long = data.longitude
        self.current_rel_alt = data.relative_altitude 
        self.current_alt = data.altitude

    def fly_path(self, waypoint_data):
        waypoints = [build_waypoint(datum) for datum in waypoint_data]
        # Execute flight plan
        self.command_service(roscopter.srv.APMCommandRequest.CMD_ARM)
        print('Armed')
        self.command_service(roscopter.srv.APMCommandRequest.CMD_LAUNCH)
        print('Launched')
        time.sleep(5)
        self.trigger_auto_service()
        self.adjust_throttle_service()
        for waypoint in waypoints:
            self.send_waypoint(waypoint)
        self.command_service(roscopter.srv.APMCommandRequest.CMD_LAND)
        print('Landing')

    def on_position_update(self, data):
        '''
        data: GPS + IMU
        '''
        print("Updating pos RAWRAWRAWRAWR")
        self.current_data = data
        self.current_lat = data.longitude
        self.current_long = data.latitude
        self.current_alt = data.altitude

def build_waypoint(data):
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
    return int(coordinate * 1e+7)


def open_waypoint_file(filename):
    f = open(filename)
    waypoints = json.load(f)
    return waypoints


def callback(data):
    rospy.loginfo(rospy.get_caller_id() + "Long: %s", data.longitude)
    print"RAWRAWRAWRWAR", data.longitude


def get_pos():
    for i in range (10):
        time.sleep(2)
        rospy.spin()

def main():
    rospy.init_node("quadcopter_brain")
    carl = QuadcopterBrain()
    carl.clear_waypoints_service()
    great_lawn_waypoints = open_waypoint_file(
        "waypoint_data/great_lawn_waypoints.json")
    print carl.reached_waypoint(great_lawn_waypoints['A'])
    carl.fly_path([great_lawn_waypoints['A'], great_lawn_waypoints['B'],
                   great_lawn_waypoints['C']])
    rospy.spin()
   

if __name__ == '__main__':
    main()
    #test_pos_sub()
