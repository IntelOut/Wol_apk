# Privacy Policy

**Last updated: June 7, 2026**

## 1. Introduction

This Privacy Policy describes how the "Wake on LAN" mobile application ("the App") handles user data. The App is a utility tool that sends Wake-on-LAN magic packets to wake up devices on a local network.

## 2. Data Collection and Use

### 2.1. Information You Provide

The App stores the following data locally on your device:
- **MAC addresses** of devices you add to the saved devices list
- **Device names** that you assign to those MAC addresses

### 2.2. Network Data Transmission

When you use the "Wake Up" function, the App transmits a UDP broadcast packet containing:
- The MAC address of the target device (as part of the WOL magic packet structure)
- The target IP address and port you specified

This transmission occurs **only over your local network** and is not sent to external servers.

### 2.3. No Account Required

The App does **not** require user registration, login, or any account creation.

## 3. Data Storage and Security

- All saved device lists are stored **locally** on your device using AES-256 encryption (`flet.security.encrypt`)
- No data is transmitted to external servers, cloud services, or third parties
- No analytics or tracking services are used

## 4. Permissions

The App requires the following Android permissions:
- **INTERNET**: Required to send UDP broadcast packets on the local network
- **ACCESS_NETWORK_STATE**: Required to check network connectivity

These permissions are used exclusively for the core WOL functionality.

## 5. Third-Party Services

The App does **not** integrate any third-party analytics, advertising, or tracking services.

## 6. Data Deletion

All stored data can be deleted by:
- Deleting individual devices through the App's interface (swipe-to-delete or delete button)
- Uninstalling the App, which removes all locally stored data

## 7. Children's Privacy

The App does not knowingly collect any personal information from children under the age of 13.

## 8. Changes to This Privacy Policy

We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated revision date.

## 9. Contact

If you have any questions about this Privacy Policy, please contact the developer through the Google Play Store listing.

---

*This Privacy Policy is provided for informational purposes and does not constitute legal advice. You may need to consult with a legal professional to ensure compliance with applicable laws.*
