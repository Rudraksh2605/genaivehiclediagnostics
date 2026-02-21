#include <cstdint>
#include <mutex>
#include <string>
#include <iostream>
#include <thread>
#include <chrono>

enum class AlertType : std::uint8_t
{
    None = 0,
    SpeedHigh = 1,
    SpeedLow = 2,
    BatteryLow = 4,
    TirePressureLow = 8,
    MultipleAlerts = 16
};

class VehicleMonitor
{
private:
    std::int32_t m_currentSpeedKmh;
    std::uint8_t m_currentBatterySoC;
    std::int32_t m_currentTirePressureKpa;
    std::int32_t m_speedThresholdHighKmh;
    std::int32_t m_speedThresholdLowKmh;
    std::uint8_t m_batteryThresholdLowSoC;
    std::int32_t m_tirePressureThresholdLowKpa;
    mutable std::mutex m_monitorMutex;

public:
    VehicleMonitor(
        std::int32_t initialSpeedKmh,
        std::uint8_t initialBatterySoC,
        std::int32_t initialTirePressureKpa,
        std::int32_t speedHighKmh,
        std::int32_t speedLowKmh,
        std::uint8_t batteryLowSoC,
        std::int32_t tirePressureLowKpa)
    : m_currentSpeedKmh(initialSpeedKmh),
      m_currentBatterySoC(initialBatterySoC),
      m_currentTirePressureKpa(initialTirePressureKpa),
      m_speedThresholdHighKmh(speedHighKmh),
      m_speedThresholdLowKmh(speedLowKmh),
      m_batteryThresholdLowSoC(batteryLowSoC),
      m_tirePressureThresholdLowKpa(tirePressureLowKpa)
    {}

    void updateParameters(
        std::int32_t newSpeedKmh,
        std::uint8_t newBatterySoC,
        std::int32_t newTirePressureKpa)
    {
        std::lock_guard<std::mutex> lock(m_monitorMutex);
        m_currentSpeedKmh = newSpeedKmh;
        m_currentBatterySoC = newBatterySoC;
        m_currentTirePressureKpa = newTirePressureKpa;
    }

    AlertType checkAlerts() const
    {
        std::lock_guard<std::mutex> lock(m_monitorMutex);
        std::uint8_t alerts = static_cast<std::uint8_t>(AlertType::None);

        if (m_currentSpeedKmh > m_speedThresholdHighKmh)
        {
            alerts |= static_cast<std::uint8_t>(AlertType::SpeedHigh);
        }
        else if (m_currentSpeedKmh < m_speedThresholdLowKmh)
        {
            alerts |= static_cast<std::uint8_t>(AlertType::SpeedLow);
        }
        if (m_currentBatterySoC < m_batteryThresholdLowSoC)
        {
            alerts |= static_cast<std::uint8_t>(AlertType::BatteryLow);
        }
        if (m_currentTirePressureKpa < m_tirePressureThresholdLowKpa)
        {
            alerts |= static_cast<std::uint8_t>(AlertType::TirePressureLow);
        }
        if ((alerts != static_cast<std::uint8_t>(AlertType::None)) &&
            ((alerts & (alerts - 1)) != 0))
        {
            return AlertType::MultipleAlerts;
        }
        return static_cast<AlertType>(alerts);
    }
};

std::string getAlertString(AlertType type)
{
    std::string result = "";
    std::uint8_t alertVal = static_cast<std::uint8_t>(type);

    if (type == AlertType::MultipleAlerts)
    {
        result = "Multiple Alerts";
    }
    else if (type == AlertType::None)
    {
        result = "None";
    }
    else
    {
        if ((alertVal & static_cast<std::uint8_t>(AlertType::SpeedHigh)) != 0)
        {
            result += "Speed High ";
        }
        if ((alertVal & static_cast<std::uint8_t>(AlertType::SpeedLow)) != 0)
        {
            result += "Speed Low ";
        }
        if ((alertVal & static_cast<std::uint8_t>(AlertType::BatteryLow)) != 0)
        {
            result += "Battery Low ";
        }
        if ((alertVal & static_cast<std::uint8_t>(AlertType::TirePressureLow)) != 0)
        {
            result += "Tire Pressure Low ";
        }
    }
    return result;
}

void monitorThread(VehicleMonitor& monitor)
{
    for (std::uint8_t i = 0; i < 5; ++i)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        AlertType alert = monitor.checkAlerts();
        if (alert != AlertType::None)
        {
            std::cout << "Alert: " << getAlertString(alert) << std::endl;
        }
    }
}

void updateThread(VehicleMonitor& monitor)
{
    monitor.updateParameters(100, 90, 250);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    monitor.updateParameters(180, 80, 240);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    monitor.updateParameters(40, 15, 180);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    monitor.updateParameters(130, 5, 200);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    monitor.updateParameters(120, 70, 150);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    monitor.updateParameters(100, 90, 250);
}

int main()
{
    std::int32_t initialSpeed = 100;
    std::uint8_t initialBattery = 90;
    std::int32_t initialTirePressure = 250;
    std::int32_t speedHighThreshold = 160;
    std::int32_t speedLowThreshold = 50;
    std::uint8_t batteryLowThreshold = 10;
    std::int32_t tirePressureLowThreshold = 200;

    VehicleMonitor monitor(
        initialSpeed,
        initialBattery,
        initialTirePressure,
        speedHighThreshold,
        speedLowThreshold,
        batteryLowThreshold,
        tirePressureLowThreshold);

    std::thread t1(monitorThread, std::ref(monitor));
    std::thread t2(updateThread, std::ref(monitor));

    t1.join();
    t2.join();

    return 0;
}