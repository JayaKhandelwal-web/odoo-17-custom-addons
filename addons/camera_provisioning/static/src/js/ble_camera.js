/** @odoo-module **/

/**
 * BLE Camera Provisioning for Odoo 17
 * 
 * This module handles Bluetooth Low Energy communication with
 * XiongMai (XM) based cameras like COFE PTZ cameras.
 * 
 * BLE Protocol Details (captured from nRF Connect):
 * - Service UUID: 0x1910 (WiFi Provisioning)
 * - Write Characteristic: 0x2B11 (Send WiFi credentials)
 * - Notify Characteristic: 0x2B10 (Receive status)
 * 
 * Developed for Annapurna Travels
 */

// BLE UUIDs for XiongMai cameras
const BLE_CONFIG = {
    // Service UUID for WiFi provisioning
    SERVICE_UUID: 0x1910,
    
    // Characteristic for writing WiFi credentials
    WRITE_CHAR_UUID: 0x2B11,
    
    // Characteristic for receiving notifications/status
    NOTIFY_CHAR_UUID: 0x2B10,
    
    // Notification descriptor
    NOTIFY_DESCRIPTOR_UUID: 0x2902,
    
    // Device name prefixes to scan for
    DEVICE_NAME_PREFIXES: ['XM', 'BallCamera', 'COFE', 'IPC'],
    
    // Manufacturer ID (XiongMai)
    MANUFACTURER_ID: 0x8B8B,
};

// WiFi Configuration Command Types
const WIFI_CMD = {
    SET_SSID: 0x01,
    SET_PASSWORD: 0x02,
    CONNECT: 0x03,
    STATUS: 0x04,
    SCAN_NETWORKS: 0x05,
};

// Response Status Codes
const RESPONSE_STATUS = {
    SUCCESS: 0x00,
    CONNECTING: 0x01,
    CONNECTED: 0x02,
    FAILED: 0x03,
    WRONG_PASSWORD: 0x04,
    NO_NETWORK: 0x05,
};

/**
 * Main BLE Camera Manager Class
 */
export class BLECameraManager {
    constructor() {
        this.device = null;
        this.server = null;
        this.service = null;
        this.writeCharacteristic = null;
        this.notifyCharacteristic = null;
        this.isConnected = false;
        this.onStatusUpdate = null;
    }

    /**
     * Check if Web Bluetooth is supported
     */
    static isSupported() {
        return navigator.bluetooth !== undefined;
    }

    /**
     * Check if running in secure context (HTTPS)
     */
    static isSecureContext() {
        return window.isSecureContext;
    }

    /**
     * Scan for BLE cameras
     * Returns a Bluetooth device or throws an error
     */
    async scanForCamera() {
        if (!BLECameraManager.isSupported()) {
            throw new Error('Web Bluetooth is not supported in this browser. Please use Chrome, Edge, or Opera.');
        }

        if (!BLECameraManager.isSecureContext()) {
            throw new Error('Web Bluetooth requires HTTPS. Please access Odoo via HTTPS.');
        }

        console.log('[BLE] Scanning for cameras...');
        
        try {
            // Request device with filters
            this.device = await navigator.bluetooth.requestDevice({
                filters: [
                    // Filter by name prefixes
                    ...BLE_CONFIG.DEVICE_NAME_PREFIXES.map(prefix => ({
                        namePrefix: prefix
                    })),
                ],
                optionalServices: [BLE_CONFIG.SERVICE_UUID],
            });

            console.log('[BLE] Device found:', this.device.name, this.device.id);
            
            // Add disconnect listener
            this.device.addEventListener('gattserverdisconnected', () => {
                console.log('[BLE] Device disconnected');
                this.isConnected = false;
                if (this.onStatusUpdate) {
                    this.onStatusUpdate('disconnected', 'Camera disconnected');
                }
            });

            return {
                name: this.device.name,
                id: this.device.id,
            };
        } catch (error) {
            if (error.name === 'NotFoundError') {
                throw new Error('No camera found. Make sure the camera is in pairing mode (reset it).');
            }
            throw error;
        }
    }

    /**
     * Connect to the selected camera
     */
    async connect() {
        if (!this.device) {
            throw new Error('No device selected. Please scan first.');
        }

        console.log('[BLE] Connecting to GATT server...');
        this.server = await this.device.gatt.connect();
        
        console.log('[BLE] Getting WiFi provisioning service...');
        this.service = await this.server.getPrimaryService(BLE_CONFIG.SERVICE_UUID);
        
        console.log('[BLE] Getting characteristics...');
        
        // Get write characteristic
        this.writeCharacteristic = await this.service.getCharacteristic(BLE_CONFIG.WRITE_CHAR_UUID);
        console.log('[BLE] Write characteristic ready');
        
        // Get notify characteristic and enable notifications
        this.notifyCharacteristic = await this.service.getCharacteristic(BLE_CONFIG.NOTIFY_CHAR_UUID);
        
        // Start notifications
        await this.notifyCharacteristic.startNotifications();
        this.notifyCharacteristic.addEventListener('characteristicvaluechanged', 
            this._handleNotification.bind(this));
        console.log('[BLE] Notifications enabled');
        
        this.isConnected = true;
        return true;
    }

    /**
     * Handle notifications from camera
     */
    _handleNotification(event) {
        const value = event.target.value;
        const data = new Uint8Array(value.buffer);
        
        console.log('[BLE] Notification received:', Array.from(data).map(b => b.toString(16)).join(' '));
        
        // Parse response
        if (data.length >= 2) {
            const cmd = data[0];
            const status = data[1];
            
            let statusText = '';
            switch (status) {
                case RESPONSE_STATUS.SUCCESS:
                    statusText = 'Success';
                    break;
                case RESPONSE_STATUS.CONNECTING:
                    statusText = 'Connecting to WiFi...';
                    break;
                case RESPONSE_STATUS.CONNECTED:
                    statusText = 'Connected to WiFi!';
                    break;
                case RESPONSE_STATUS.FAILED:
                    statusText = 'Connection failed';
                    break;
                case RESPONSE_STATUS.WRONG_PASSWORD:
                    statusText = 'Wrong WiFi password';
                    break;
                case RESPONSE_STATUS.NO_NETWORK:
                    statusText = 'WiFi network not found';
                    break;
                default:
                    statusText = `Unknown status: ${status}`;
            }
            
            if (this.onStatusUpdate) {
                this.onStatusUpdate(status, statusText);
            }
        }
    }

    /**
     * Encode string to bytes with length prefix
     */
    _encodeString(str) {
        const encoder = new TextEncoder();
        const bytes = encoder.encode(str);
        return new Uint8Array([bytes.length, ...bytes]);
    }

    /**
     * Build WiFi configuration packet
     * 
     * Packet format (XiongMai protocol):
     * [0x00] [SSID_LEN] [SSID...] [PASS_LEN] [PASS...] [CHECKSUM]
     */
    _buildWiFiPacket(ssid, password) {
        const ssidBytes = new TextEncoder().encode(ssid);
        const passBytes = new TextEncoder().encode(password);
        
        // Build packet
        const packet = new Uint8Array(1 + 1 + ssidBytes.length + 1 + passBytes.length + 1);
        let offset = 0;
        
        // Header byte
        packet[offset++] = 0x00;
        
        // SSID length + SSID
        packet[offset++] = ssidBytes.length;
        packet.set(ssidBytes, offset);
        offset += ssidBytes.length;
        
        // Password length + Password
        packet[offset++] = passBytes.length;
        packet.set(passBytes, offset);
        offset += passBytes.length;
        
        // Checksum (XOR of all bytes)
        let checksum = 0;
        for (let i = 0; i < offset; i++) {
            checksum ^= packet[i];
        }
        packet[offset] = checksum;
        
        return packet;
    }

    /**
     * Alternative packet format (some XM cameras use this)
     */
    _buildWiFiPacketV2(ssid, password) {
        const ssidBytes = new TextEncoder().encode(ssid);
        const passBytes = new TextEncoder().encode(password);
        
        // Format: [CMD] [TOTAL_LEN] [SSID_LEN] [SSID] [PASS_LEN] [PASS]
        const totalLen = 2 + ssidBytes.length + 1 + passBytes.length;
        const packet = new Uint8Array(2 + totalLen);
        
        let offset = 0;
        packet[offset++] = 0x01;  // Command: Set WiFi
        packet[offset++] = totalLen;
        packet[offset++] = ssidBytes.length;
        packet.set(ssidBytes, offset);
        offset += ssidBytes.length;
        packet[offset++] = passBytes.length;
        packet.set(passBytes, offset);
        
        return packet;
    }

    /**
     * Send WiFi credentials to camera
     */
    async sendWiFiCredentials(ssid, password) {
        if (!this.isConnected || !this.writeCharacteristic) {
            throw new Error('Not connected to camera');
        }

        console.log(`[BLE] Sending WiFi credentials - SSID: ${ssid}`);
        
        // Build packet
        const packet = this._buildWiFiPacket(ssid, password);
        console.log('[BLE] Packet:', Array.from(packet).map(b => b.toString(16).padStart(2, '0')).join(' '));
        
        // Send to camera
        await this.writeCharacteristic.writeValue(packet);
        console.log('[BLE] Credentials sent successfully');
        
        if (this.onStatusUpdate) {
            this.onStatusUpdate('sent', 'WiFi credentials sent, waiting for camera to connect...');
        }
        
        return true;
    }

    /**
     * Send connect command (some cameras need explicit connect after credentials)
     */
    async sendConnectCommand() {
        if (!this.isConnected || !this.writeCharacteristic) {
            throw new Error('Not connected to camera');
        }

        const packet = new Uint8Array([WIFI_CMD.CONNECT, 0x00]);
        await this.writeCharacteristic.writeValue(packet);
        console.log('[BLE] Connect command sent');
    }

    /**
     * Disconnect from camera
     */
    disconnect() {
        if (this.device && this.device.gatt.connected) {
            this.device.gatt.disconnect();
        }
        this.isConnected = false;
        this.device = null;
        this.server = null;
        this.service = null;
        this.writeCharacteristic = null;
        this.notifyCharacteristic = null;
    }

    /**
     * Get device info
     */
    getDeviceInfo() {
        if (!this.device) {
            return null;
        }
        return {
            name: this.device.name,
            id: this.device.id,
            connected: this.isConnected,
        };
    }
}

/**
 * Complete provisioning flow
 * Use this function from Odoo to provision a camera
 */
export async function provisionCamera(ssid, password, onStatus) {
    const manager = new BLECameraManager();
    
    // Set up status callback
    manager.onStatusUpdate = onStatus || ((status, message) => {
        console.log(`[Provisioning] ${status}: ${message}`);
    });

    try {
        // Step 1: Scan for camera
        onStatus && onStatus('scanning', 'Scanning for cameras... Please select your camera.');
        const device = await manager.scanForCamera();
        onStatus && onStatus('found', `Found camera: ${device.name}`);

        // Step 2: Connect
        onStatus && onStatus('connecting', 'Connecting to camera...');
        await manager.connect();
        onStatus && onStatus('connected', 'Connected! Sending WiFi credentials...');

        // Step 3: Send credentials
        await manager.sendWiFiCredentials(ssid, password);
        
        // Step 4: Wait for connection (camera will notify)
        // The actual result comes via notification callback
        
        return {
            success: true,
            device: device,
            manager: manager,
        };
    } catch (error) {
        onStatus && onStatus('error', error.message);
        manager.disconnect();
        throw error;
    }
}

// Export for global access
window.BLECameraManager = BLECameraManager;
window.provisionCamera = provisionCamera;

export default BLECameraManager;
