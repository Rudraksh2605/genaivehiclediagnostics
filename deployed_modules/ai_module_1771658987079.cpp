#include <cstdint>
#include <vector>
#include <mutex>
#include <utility>

enum class AlertType : std::uint8_t
{
    NONE = 0U,
    SPEED_LOW = 1U,
    SPEED_HIGH = 2U,
    BATTERY_LOW = 3U,
    TIRE_PRESSURE_LOW = 4U,
    TIRE_PRESSURE_HIGH = 5U
};

struct Alert
{
    AlertType type;
    std::int32_t value;

    Alert(AlertType t, std::int32_t v) : type(t), value(v) {}
};

class VehicleMonitor
{
public:
    explicit VehicleMonitor(
        std::int32_t minSpeedThreshold,
        std::int32_t maxSpeedThreshold,
        std::uint8_t minBatterySoCThreshold,
        std::int32_t minTirePressureThreshold,
        std::int32_t maxTirePressureThreshold)
        : m_minSpeedThreshold(minSpeedThreshold),
          m_maxSpeedThreshold(maxSpeedThreshold),
          m_minBatterySoCThreshold(minBatterySoCThreshold),
          m_minTirePressureThreshold(minTirePressureThreshold),
          m_maxTirePressureThreshold(maxTirePressureThreshold),
          m_currentSpeed(0),
          m_currentBatterySoC(0U),
          m_currentTirePressure(0)
    {}

    void updateSpeed(std::int32_t speed)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_currentSpeed = speed;
    }

    void updateBatterySoC(std::uint8_t soc)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_currentBatterySoC = soc;
    }

    void updateTirePressure(std::int32_t pressure)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_currentTirePressure = pressure;
    }

    std::vector<Alert> checkAndGetAlerts()
    {
        std::vector<Alert> alerts;
        std::int32_t currentSpeedCopy;
        std::uint8_t currentBatterySoCCopy;
        std::int32_t currentTirePressureCopy;

        {
            std::lock_guard<std::mutex> lock(m_mutex);
            currentSpeedCopy = m_currentSpeed;
            currentBatterySoCCopy = m_currentBatterySoC;
            currentTirePressureCopy = m_currentTirePressure;
        }

        if (currentSpeedCopy < m_minSpeedThreshold)
        {
            alerts.emplace_back(AlertType::SPEED_LOW, currentSpeedCopy);
        }
        else if (currentSpeedCopy > m_maxSpeedThreshold)
        {
            alerts.emplace_back(AlertType::SPEED_HIGH, currentSpeedCopy);
        }

        if (currentBatterySoCCopy < m_minBatterySoCThreshold)
        {
            alerts.emplace_back(AlertType::BATTERY_LOW, static_cast<std::int32_t>(currentBatterySoCCopy));
        }

        if (currentTirePressureCopy < m_minTirePressureThreshold)
        {
            alerts.emplace_back(AlertType::TIRE_PRESSURE_LOW, currentTirePressureCopy);
        }
        else if (currentTirePressureCopy > m_maxTirePressureThreshold)
        {
            alerts.emplace_back(AlertType::TIRE_PRESSURE_HIGH, currentTirePressureCopy);
        }

        return alerts;
    }

private:
    std::mutex m_mutex;

    const std::int32_t m_minSpeedThreshold;
    const std::int32_t m_maxSpeedThreshold;
    const std::uint8_t m_minBatterySoCThreshold;
    const std::int32_t m_minTirePressureThreshold;
    const std::int32_t m_maxTirePressureThreshold;

    std::int32_t m_currentSpeed;
    std::uint8_t m_currentBatterySoC;
    std::int32_t m_currentTirePressure;
};