#ifdef BOOST_FILESYSTEM
  #include <boost/filesystem.hpp>
  namespace fs = boost::filesystem;
#else
  #include <filesystem>
  namespace fs = std::filesystem;
#endif