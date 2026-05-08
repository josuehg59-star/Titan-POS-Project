# 🛡️ TITÁN: AI-Powered Autonomous Surveillance System

![Project Status](https://img.shields.io/badge/Status-Stable-success)
![Language](https://img.shields.io/badge/Language-Python-blue)
![AI](https://img.shields.io/badge/AI-OpenCV%20HOG-orange)

**Titán** is a high-precision, autonomous security ecosystem designed to protect a 2018 Toyota Yaris using a "Triple Shield" architecture. It combines Computer Vision, Cloud Infrastructure, and Local Redundancy to ensure 24/7 security with zero false alarms.

---

## 🚀 Key Features

*   **Triple Shield Architecture**:
    *   **Level 1: Real-Time Mobile Alerts**: Instant high-priority push notifications via Firebase Cloud Messaging (FCM).
    *   **Level 2: Cloud Storage**: Automatic backup of video evidence and logs to a remote PocketBase server.
    *   **Level 3: Local Redundancy**: Persistent local logging (JSON) and video buffering for network-independent reliability.
*   **Intelligent Human Detection**: Uses OpenCV (HOG Descriptor) with custom calibration to distinguish humans from environmental noise, traffic, or animals.
*   **Dual-Alert Protocol**:
    *   **Critical Alerts**: Audible sirens for vehicle proximity (Cameras 1 & 2).
    *   **Silent Alerts**: Perimeter monitoring with visual-only notifications (Cameras 3 & 4).
*   **Autonomous Maintenance**: Self-cleaning logic that purges data every 12 hours to maintain system performance and prevent storage saturation.

## 🛠️ Technology Stack

*   **Backend**: Python (OpenCV, Requests, Threading).
*   **Mobile Connectivity**: Firebase (FCM).
*   **Database/Server**: PocketBase (Admin Auth Integration).
*   **Vision**: HOG Descriptor + Custom Aspect Ratio Filtering.

---

## 🇪🇸 Resumen en Español

**Titán** es un ecosistema de seguridad autónoma diseñado para proteger un Toyota Yaris 2018 mediante una arquitectura de "Triple Escudo". Combina Visión Artificial, Infraestructura en la Nube y Redundancia Local.

*   **Detección Humana**: IA calibrada para ignorar falsas alarmas (coches, perros).
*   **Notificaciones Inteligentes**: Sirena para áreas críticas, alertas silenciosas para el perímetro.
*   **Auto-Mantenimiento**: Purga automática de datos cada 12 horas.

---

## 👤 Developer
**Josue Hernandez Gutierrez**  
*Full Stack Developer & AI Integration Enthusiast*

---
> [!NOTE]
> This project was developed as a real-world implementation of AI in vehicle security.
