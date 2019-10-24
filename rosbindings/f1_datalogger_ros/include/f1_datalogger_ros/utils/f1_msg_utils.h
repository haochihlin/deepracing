#ifndef F1_DATALOGGER_ROS_F1_MSG_UTILS_H
#define F1_DATALOGGER_ROS_F1_MSG_UTILS_H
#include "f1_datalogger/car_data/timestamped_car_data.h"
#include "f1_datalogger_msgs/msg/packet_header.hpp"
#include "f1_datalogger_msgs/msg/packet_motion_data.hpp"
#include "f1_datalogger_msgs/msg/car_motion_data.hpp"
namespace f1_datalogger_ros
{
    class F1MsgUtils
    {
    public:
        F1MsgUtils() = default;
        void doNothing();
        static f1_datalogger_msgs::msg::PacketHeader toROS(const deepf1::twenty_eighteen::PacketHeader& header_data);
        static f1_datalogger_msgs::msg::PacketMotionData toROS(const deepf1::twenty_eighteen::PacketMotionData& motion_data);
        static f1_datalogger_msgs::msg::CarMotionData toROS(const deepf1::twenty_eighteen::CarMotionData& motion_data);

    };
}
#endif