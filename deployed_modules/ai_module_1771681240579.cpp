#include <cstdint>
#include <iostream>
#include <thread>
#include <atomic>
#include <chrono>
#include <functional>
#include <mutex>
#include <utility>

class CanBusSimulator
{
public:
    explicit CanBusSimulator() = default;
    std::uint16_t readSpeedKmh() const
    {
        static std::uint16_t currentSpeedKmh = 0U;
        static std::uint8_t updateCounter = 0U;
        updateCounter = static_cast<std::uint8_t>(updateCounter + 1U);
        if ((updateCounter % 5U) == 0U)
        {
            currentSpeedKmh = static_cast<std::uint16_t>(currentSpeedKmh + 10U);
            if (currentSpeedKmh > 150U)
            {
                currentSpeedKmh = 50U;
            }
        }
        return currentSpeedKmh;
    }
};

enum class SpeedAlertLevel : std::uint8_t
{
    NoAlert = 0U,
    ExceededThreshold = 1U
};

class SpeedMonitorService
{
public:
    explicit SpeedMonitorService(std::uint16_t initialThresholdKmh, std::function<void(std::uint16_t, std::uint16_t)> alertCallback)
        : speedThresholdKmh_(initialThresholdKmh),
          running_(false),
          alertCallback_(std::move(alertCallback)),
          canBusSimulator_()
    {
    }

    SpeedMonitorService(const SpeedMonitorService&) = delete;
    SpeedMonitorService& operator=(const SpeedMonitorService&) = delete;
    SpeedMonitorService(SpeedMonitorService&&) = delete;
    SpeedMonitorService& operator=(SpeedMonitorService&&) = delete;

    ~SpeedMonitorService()
    {
        stop();
    }

    void start()
    {
        if (!running_.load())
        {
            running_.store(true);
            serviceThread_ = std::thread(&SpeedMonitorService::monitorLoop, this);
        }
    }

    void stop()
    {
        if (running_.load())
        {
            running_.store(false);
            if (serviceThread_.joinable())
            {
                serviceThread_.join();
            }
        }
    }

    void setSpeedThreshold(std::uint16_t newThresholdKmh)
    {
        std::lock_guard<std::mutex> lock(thresholdMutex_);
        speedThresholdKmh_ = newThresholdKmh;
    }

private:
    std::uint16_t speedThresholdKmh_;
    std::atomic_bool running_;
    std::thread serviceThread_;
    std::function<void(std::uint16_t, std::uint16_t)> alertCallback_;
    CanBusSimulator canBusSimulator_;
    std::mutex thresholdMutex_;

    void monitorLoop()
    {
        while (running_.load())
        {
            std::uint16_t currentSpeed = canBusSimulator_.readSpeedKmh();
            std::uint16_t thresholdToUse;
            {
                std::lock_guard<std::mutex> lock(thresholdMutex_);
                thresholdToUse = speedThresholdKmh_;
            }

            if (currentSpeed > thresholdToUse)
            {
                alertCallback_(currentSpeed, thresholdToUse);
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100U));
        }
    }
};

int main()
{
    std::uint16_t initialThreshold = 100U;

    auto alertHandler = [](std::uint16_t currentSpeed, std::uint16_t threshold)
    {
        std::cout << "ALERT: Speed " << currentSpeed << " km/h exceeds threshold " << threshold << " km/h\n";
    };

    SpeedMonitorService monitor(initialThreshold, alertHandler);

    monitor.start();

    std::this_thread::sleep_for(std::chrono::seconds(5U));
    monitor.setSpeedThreshold(80U);
    std::this_thread::sleep_for(std::chrono::seconds(5U));
    monitor.setSpeedThreshold(120U);
    std::this_thread::sleep_for(std::chrono::seconds(5U));

    monitor.stop();

    return 0;
}