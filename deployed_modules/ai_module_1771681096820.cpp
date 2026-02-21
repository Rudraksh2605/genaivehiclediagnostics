#include <cstdint>
#include <iostream>
#include <string>
#include <mutex>

enum class AlertLevel : uint8_t {
    OK = 0U,
    WARNING = 1U,
    CRITICAL = 2U
};

class VehicleMonitor {
private:
    float m_speed;
    float m_batterySoC;
    float m_tirePressure;

    float m_speedThresholdWarning;
    float m_speedThresholdCritical;

    float m_batterySoCThresholdWarningLow;
    float m_batterySoCThresholdCriticalLow;

    float m_tirePressureThresholdWarningLow;
    float m_tirePressureThresholdWarningHigh;
    float m_tirePressureThresholdCriticalLow;
    float m_tirePressureThresholdCriticalHigh;

    std::mutex m_mutex;

    void checkSpeedAlerts() {
        if (m_speed > m_speedThresholdCritical) {
            std::cout << "CRITICAL: Speed " << m_speed << " km/h exceeds critical limit " << m_speedThresholdCritical << " km/h.\n";
        } else if (m_speed > m_speedThresholdWarning) {
            std::cout << "WARNING: Speed " << m_speed << " km/h exceeds warning limit " << m_speedThresholdWarning << " km/h.\n";
        }
    }

    void checkBatterySoCAlerts() {
        if (m_batterySoC < m_batterySoCThresholdCriticalLow) {
            std::cout << "CRITICAL: Battery SoC " << m_batterySoC << "% is below critical limit " << m_batterySoCThresholdCriticalLow << "%.\n";
        } else if (m_batterySoC < m_batterySoCThresholdWarningLow) {
            std::cout << "WARNING: Battery SoC " << m_batterySoC << "% is below warning limit " << m_batterySoCThresholdWarningLow << "%.\n";
        }
    }

    void checkTirePressureAlerts() {
        if (m_tirePressure < m_tirePressureThresholdCriticalLow) {
            std::cout << "CRITICAL: Tire pressure " << m_tirePressure << " psi is below critical limit " << m_tirePressureThresholdCriticalLow << " psi.\n";
        } else if (m_tirePressure > m_tirePressureThresholdCriticalHigh) {
            std::cout << "CRITICAL: Tire pressure " << m_tirePressure << " psi is above critical limit " << m_tirePressureThresholdCriticalHigh << " psi.\n";
        } else if (m_tirePressure < m_tirePressureThresholdWarningLow) {
            std::cout << "WARNING: Tire pressure " << m_tirePressure << " psi is below warning limit " << m_tirePressureThresholdWarningLow << " psi.\n";
        } else if (m_tirePressure > m_tirePressureThresholdWarningHigh) {
            std::cout << "WARNING: Tire pressure " << m_tirePressure << " psi is above warning limit " << m_tirePressureThresholdWarningHigh << " psi.\n";
        }
    }

public:
    VehicleMonitor(
        float initialSpeed, float initialBatterySoC, float initialTirePressure,
        float speedWarn, float speedCrit,
        float batterySoCWarnLow, float batterySoCCritLow,
        float tirePressureWarnLow, float tirePressureWarnHigh,
        float tirePressureCritLow, float tirePressureCritHigh
    ) :
        m_speed(initialSpeed),
        m_batterySoC(initialBatterySoC),
        m_tirePressure(initialTirePressure),
        m_speedThresholdWarning(speedWarn),
        m_speedThresholdCritical(speedCrit),
        m_batterySoCThresholdWarningLow(batterySoCWarnLow),
        m_batterySoCThresholdCriticalLow(batterySoCCritLow),
        m_tirePressureThresholdWarningLow(tirePressureWarnLow),
        m_tirePressureThresholdWarningHigh(tirePressureWarnHigh),
        m_tirePressureThresholdCriticalLow(tirePressureCritLow),
        m_tirePressureThresholdCriticalHigh(tirePressureCritHigh)
    {}

    void updateSpeed(float speed) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_speed = speed;
    }

    void updateBatterySoC(float soc) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_batterySoC = soc;
    }

    void updateTirePressure(float pressure) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_tirePressure = pressure;
    }

    void checkAndReportAlerts() {
        std::lock_guard<std::mutex> lock(m_mutex);
        checkSpeedAlerts();
        checkBatterySoCAlerts();
        checkTirePressureAlerts();
    }

    float getSpeed() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_speed;
    }

    float getBatterySoC() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_batterySoC;
    }

    float getTirePressure() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_tirePressure;
    }
};

int main() {
    float initialSpeed = 80.0F;
    float initialBatterySoC = 75.0F;
    float initialTirePressure = 32.0F;

    float speedWarn = 100.0F;
    float speedCrit = 120.0F;

    float batterySoCWarnLow = 20.0F;
    float batterySoCCritLow = 10.0F;

    float tirePressureWarnLow = 28.0F;
    float tirePressureWarnHigh = 35.0F;
    float tirePressureCritLow = 25.0F;
    float tirePressureCritHigh = 40.0F;

    VehicleMonitor monitor(
        initialSpeed, initialBatterySoC, initialTirePressure,
        speedWarn, speedCrit,
        batterySoCWarnLow, batterySoCCritLow,
        tirePressureWarnLow, tirePressureWarnHigh,
        tirePressureCritLow, tirePressureCritHigh
    );

    std::cout << "Initial status:\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateSpeed(105.0F);
    std::cout << "After speed update (105 km/h):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateSpeed(125.0F);
    std::cout << "After speed update (125 km/h):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateBatterySoC(15.0F);
    std::cout << "After battery SoC update (15%):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateBatterySoC(5.0F);
    std::cout << "After battery SoC update (5%):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateTirePressure(27.0F);
    std::cout << "After tire pressure update (27 psi):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateTirePressure(36.0F);
    std::cout << "After tire pressure update (36 psi):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateTirePressure(24.0F);
    std::cout << "After tire pressure update (24 psi):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateTirePressure(41.0F);
    std::cout << "After tire pressure update (41 psi):\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    monitor.updateSpeed(90.0F);
    monitor.updateBatterySoC(50.0F);
    monitor.updateTirePressure(32.0F);
    std::cout << "After all parameters reset to OK:\n";
    monitor.checkAndReportAlerts();
    std::cout << "\n";

    return 0;
}