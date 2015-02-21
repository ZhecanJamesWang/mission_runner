import rospy
# TODO: Determine if this import is needed
# import roscopter
import roscopter.msg
import roscopter.srv
import std_srvs.srv

from position_tools import PositionTools


class Quadcopter(object):
    def __init__(self):
        rospy.init_node("Quadcopter")
        self._clear_waypoints_service = rospy.ServiceProxy(
            'clear_waypoints', std_srvs.srv.Empty)
        self._command_service = rospy.ServiceProxy(
            'command', roscopter.srv.APMCommand)
        self._waypoint_service = rospy.ServiceProxy(
            'waypoint', roscopter.srv.SendWaypoint)
        self._trigger_auto_service = rospy.ServiceProxy(
            'trigger_auto', std_srvs.srv.Empty)
        self._adjust_throttle_service = rospy.ServiceProxy(
            'adjust_throttle', std_srvs.srv.Empty)

        self.current_lat = 0.0
        self.current_long = 0.0
        self.current_rel_alt = 0.0
        self.current_alt = 0.0
        self.heading = 0.0
        rospy.Subscriber("/filtered_pos", roscopter.msg.FilteredPosition,
                         self._position_callback)

    def _position_callback(self, data):
        self.current_lat = PositionTools.mavlink_to_gps(data.latitude)
        self.current_long = PositionTools.mavlink_to_gps(data.longitude)
        self.current_rel_alt = data.relative_altitude / 1000.0  # From mm to m
        self.current_alt = data.altitude / 1000.0  # From mm to m
        self.heading = data.heading
# Work
    def arm(self):
        self._command_service(roscopter.srv.APMCommandRequest.CMD_ARM)
        print('Armed')

    def launch(self, system_wait=5):
        self._command_service(roscopter.srv.APMCommandRequest.CMD_LAUNCH)
        print('Launched, waiting for %d seconds' % (system_wait))
        rospy.sleep(system_wait)

    def land(self):
        self._command_service(roscopter.srv.APMCommandRequest.CMD_LAND)
        print('Landing')

# Work
    def clear_waypoints(self):
        self._clear_waypoints_service()

# Work
    def send_waypoint(self, waypoint, max_num_tries=5):
        self._set_auto_mode()
        sent_waypoint = False
        tries = 0

        while not sent_waypoint and tries < max_num_tries:
            res = self._waypoint_service(waypoint)
            sent_waypoint = res.result
            tries += 1
            self._print_send_waypoint_status(
                sent_waypoint, tries, max_num_tries)
            rospy.sleep(0.1)

        return sent_waypoint

    def _print_send_waypoint_status(self, sent_waypoint, tries, max_num_tries):
        if sent_waypoint:
            print('Sent waypoint %d, %d' % (waypoint.latitude,
                                            waypoint.longitude))
        else:
            print("Failed to send waypoint %d, %d" % (waypoint.latitude,
                                                      waypoint.longitude))
            if tries == max_num_tries:
                print("Tried %d times and giving up" % (tries))
            else:
                print("Retrying. Tries: %d" % (tries))


    def _set_auto_mode(self):
        '''
            TODO: Explain why it is necessary to trigger_auto and
            adjust_throttle - b/c ROSCOPTER is dumb
        '''
        self._trigger_auto_service()
        self._adjust_throttle_service()
