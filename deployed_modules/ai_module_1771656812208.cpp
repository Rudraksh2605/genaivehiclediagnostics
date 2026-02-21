#include <cstdint>
#include <vector>
#include <mutex>

enum class AlertType : uint8_t {
    SPEED_HIGH = 0U,
    SPEED_LOW = 1U,
    BATTERY_LOW = 2U,
    TIRE_PRESSURE_HIGH = 3U,
    TIRE_PRESSURE_LOW = 4U
};

enum class SensorType : uint8_t {
    SPEED = 0U,
    BATTERY_SOC = 1U,
    TIRE_PRESSURE = 2U
};

struct Alert {
    AlertType type;
    int32_t value;
    SensorType sensor;

    Alert(AlertType t, int32_t v, SensorType s) : type(t), value(v), sensor(s) {}
};

class VehicleMonitor {
private:
    std::mutex m_mutex;
    int32_t m_currentSpeedKph;
    uint8_t m_currentBatterySoCPercent;
    int32_t m_currentTirePressurePsi;

    int32_t m_speedThresholdHighKph;
    int32_t m_speedThresholdLowKph;
    uint8_t m_batteryThresholdLowPercent;
    int32_t m_tirePressureThresholdHighPsi;
    int32_t m_tirePressureThresholdLowPsi;

public:
    VehicleMonitor(int32_t speedHighKph, int32_t speedLowKph,
                   uint8_t batteryLowPercent,
                   int32_t tirePressureHighPsi, int32_t tirePressureLowPsi)
        : m_currentSpeedKph(0),
          m_currentBatterySoCPercent(100U),
          m_currentTirePressurePsi(35),
          m_speedThresholdHighKph(speedHighKph),
          m_speedThresholdLowKph(speedLowKph),
          m_batteryThresholdLowPercent(batteryLowPercent),
          m_tirePressureThresholdHighPsi(tirePressureHighPsi),
          m_tirePressureThresholdLowPsi(tirePressureLowPsi) {}

    void updateSpeed(int32_t speedKph) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_currentSpeedKph = speedKph;
    }

    void updateBatterySoC(uint8_t socPercent) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_currentBatterySoCPercent = socPercent;
    }

    void updateTirePressure(int32_t pressurePsi) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_currentTirePressurePsi = pressurePsi;
    }

    std::vector<Alert> checkAlerts() {
        std::vector<Alert> alerts;
        int32_t speed = 0;
        uint8_t soc = 0U;
        int32_t pressure = 0;

        {
            std::lock_guard<std::mutex> lock(m_mutex);
            speed = m_currentSpeedKph;
            soc = m_currentBatterySoCPercent;
            pressure = m_currentTirePressurePsi;
        }

        if (speed > m_speedThresholdHighKph) {
            alerts.emplace_back(AlertType::SPEED_HIGH, speed, SensorType::SPEED);
        } else if (speed < m_speedThresholdLowKph) {
            alerts.emplace_back(AlertType::SPEED_LOW, speed, SensorType::SPEED);
        }

        if (soc < m_batteryThresholdLowPercent) {
            alerts.emplace_back(AlertType::BATTERY_LOW, static_cast<int32_t>(soc), SensorType::BATTERY_SOC);
        }

        if (pressure > m_tirePressureThresholdHighPsi) {
            alerts.emplace_back(AlertType::TIRE_PRESSURE_HIGH, pressure, SensorType::TIRE_PRESSURE);
        } else if (pressure < m_tirePressureThresholdLowPsi) {
            alerts.emplace_back(AlertType::TIRE_PRESSURE_LOW, pressure, SensorType::TIRE_PRESSURE);
        }

        return alerts;
    }
};