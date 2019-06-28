/*
 * multi_threaded_framegrab_handler.h
 *
 *  Created on: Dec 6, 2018
 *      Author: ttw2xk
 */

#ifndef INCLUDE_IMAGE_LOGGING_COMMON_MULTI_THREADED_FRAMEGRAB_HANDLER_H_
#define INCLUDE_IMAGE_LOGGING_COMMON_MULTI_THREADED_FRAMEGRAB_HANDLER_H_
#include "f1_datalogger/image_logging/framegrab_handler.h"
#include <tbb/concurrent_queue.h>
#include <tbb/task_group.h>
#include <mutex>
#include <memory>
namespace deepf1
{

class MultiThreadedFrameGrabHandler : public IF1FrameGrabHandler
{
	using timeunit = std::chrono::milliseconds;
public:
  MultiThreadedFrameGrabHandler(std::string images_folder = "images", unsigned int thread_count = 5, bool write_json = false);
  virtual ~MultiThreadedFrameGrabHandler();
  inline bool isReady() override;
  void handleData(const TimestampedImageData& data) override;
  void init(const deepf1::TimePoint& begin, const cv::Size& window_size) override;
  const std::string getImagesFolder() const;

  void stop();
  void join();
private:
  std::shared_ptr< tbb::concurrent_queue<TimestampedImageData> >queue_;
  std::shared_ptr< tbb::task_group >  thread_pool_ ;
  bool running_;
  std::chrono::high_resolution_clock::time_point begin_;
  unsigned int thread_count_;
  tbb::atomic<unsigned long> counter_;
  std::mutex queue_mutex_;
  const std::string images_folder_;
  void workerFunc_();
  
  bool ready_;
  bool write_json_;
};

} /* namespace deepf1 */

#endif /* INCLUDE_IMAGE_LOGGING_COMMON_MULTI_THREADED_FRAMEGRAB_HANDLER_H_ */
