#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
from std_msgs.msg import Int32
from scipy.spatial import KDTree
import numpy as np

import math

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.
As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.
Once you have created dbw_node, you will update this node to use the status of traffic lights too.
Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.
TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number
MAX_DECEL = 1 # maximum deceleration


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)
        rospy.Subscriber('/obstacle_waypoint', Waypoint, self.obstacle_cb)
        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.pose = None
        self.base_waypoints = None
        self.waypoints_2d = None
        self.waypoint_tree = None
	self.stopline_wp_idx = LOOKAHEAD_WPS
        #print("check1")
        
        rospy.spin()

    def get_closest_wp_id(self):
        x = self.pose.pose.position.x
        y = self.pose.pose.position.y
        closest_idx = self.waypoint_tree.query([x, y], 1)[1]
        #check if in front or behind
        closest_coord = self.waypoints_2d[closest_idx]
        prev_coord = self.waypoints_2d[closest_idx - 1]
        #equation for hyperplane through closest_coords
        cl_vect = np.array(closest_coord)
        prev_vect = np.array(prev_coord)
        pos_vect = np.array([x, y])
        val = np.dot(cl_vect - prev_vect, pos_vect - cl_vect)
        if val > 0:
            closest_idx = (closest_idx + 1) % len(self.waypoints_2d)
        return closest_idx

    def generate_lane(self):
	lane = Lane()
	#print("generating")

	closest_idx = self.get_closest_wp_id()
	#print("closest_idx {}".format(closest_idx))
	farthest_idx = closest_idx + LOOKAHEAD_WPS
	base_wps = self.base_waypoints.waypoints[closest_idx:farthest_idx]
	
	if (self.stopline_wp_idx == -1) or (self.stopline_wp_idx == farthest_idx):
	    lane.waypoints = base_wps
	    print("Following waypoints!")
	else:
	    print("Stopping because of TrafficLight!")
	    lane.waypoints = self.decelerate_waypoints(base_wps, closest_idx)

	return lane

    def decelerate_waypoints(self, wps, closest_idx):
	temp = []
 	for i, wp in enumerate(wps):
	
	    p = Waypoint()
	    p.pose = wp.pose
	    stop_idx = max(self.stopline_wp_idx - closest_idx - 2, 0) #two wps back from line so front of car stops at line
	    dist = self.distance(wps, i, stop_idx)
	    #if i == 1 or i == len(wps)-1:
	        #print("self.stopline_wp_idx = {}".format(self.stopline_wp_idx))
	        #print("closest_idx = {}".format(closest_idx))
	        #print("i = {}".format(i))
	        #print("stop_idx = {}".format(stop_idx))
	        #print("dist = {} ---------------------".format(dist))
	    vel = math.sqrt(2 * MAX_DECEL * dist)
	    if vel < 1.0:
		vel = 0.0
	    p.twist.twist.linear.x = min(vel, wp.twist.twist.linear.x)
	    temp.append(p)

	return temp

    def publish_waypoints(self, closest_idx):
        #lane = Lane()
        #lane.header = self.base_waypoints.header
        
        #lane.waypoints = self.base_waypoints.waypoints[closest_idx:closest_idx + LOOKAHEAD_WPS]
        #self.final_waypoints_pub.publish(lane)
	
	final_lane = self.generate_lane()
	final_lane.header = self.base_waypoints.header
	#print("publishing")
	self.final_waypoints_pub.publish(final_lane)

    def pose_cb(self, msg):
        # TODO: Implement
        self.pose = msg
        if not self.waypoint_tree == None:
            closest_wp_idx = self.get_closest_wp_id()
            self.publish_waypoints(closest_wp_idx)

    def waypoints_cb(self, waypoints):
        # TODO: Implement
        self.base_waypoints = waypoints
        if self.waypoints_2d == None:
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)
            print("waypoints initialized!")

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
	#print("traffic_cb")
	#print("tl_wp = {}".format(msg.data))
        self.stopline_wp_idx = msg.data

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
