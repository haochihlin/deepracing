/*
 * f1_datagrab_manager.h
 *
 *  Created on: Dec 5, 2018
 *      Author: ttw2xk
 */

#ifndef INCLUDE_UDP_LOGGING_F1_DATAGRAB_MANAGER_H_
#define INCLUDE_UDP_LOGGING_F1_DATAGRAB_MANAGER_H_
#include <boost/asio.hpp>
#include <thread>
#include <memory>
#include "udp_logging/f1_datagrab_handler.h"
using boost::asio::ip::udp;
using boost::asio::ip::address;
namespace deepf1
{

class F1DataGrabManager
{
public:
  F1DataGrabManager(std::shared_ptr<IF1DatagrabHandler> handler, const std::string host = "127.0.0.1", const unsigned int port=20777);
  virtual ~F1DataGrabManager();

  void start();
  void stop();
private:
  boost::asio::io_service io_service_;
  udp::socket socket_;
  udp::endpoint remote_endpoint_;
  std::thread run_thread_;
  std::shared_ptr<IF1DatagrabHandler> data_handler_;
  bool running_;

  std::shared_ptr<UDPPacket> rcv_buffer_;


  void run_();
};

} /* namespace deepf1 */

#endif /* INCLUDE_UDP_LOGGING_F1_DATAGRAB_MANAGER_H_ */
