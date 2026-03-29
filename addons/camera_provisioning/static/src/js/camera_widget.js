/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BLECameraManager, provisionCamera } from "./ble_camera";

/**
 * Camera BLE Scan Component
 * Displays the scanning/provisioning interface
 */
export class CameraBLEScan extends Component {
    static template = "camera_provisioning.BLEScanTemplate";
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            isSupported: BLECameraManager.isSupported(),
            isSecure: BLECameraManager.isSecureContext(),
            status: 'idle',
            statusMessage: '',
            device: null,
            ssid: '',
            password: '',
            showWifiForm: false,
            isProvisioning: false,
        });
        
        this.manager = new BLECameraManager();
    }
    
    /**
     * Start scanning for cameras
     */
    async scanForCamera() {
        if (!this.state.isSupported) {
            this.notification.add("Web Bluetooth not supported. Use Chrome, Edge, or Opera.", {
                type: "danger",
            });
            return;
        }
        
        this.state.status = 'scanning';
        this.state.statusMessage = 'Scanning... Please select your camera from the browser popup.';
        
        try {
            const device = await this.manager.scanForCamera();
            this.state.device = device;
            this.state.status = 'found';
            this.state.statusMessage = `Found: ${device.name}`;
            this.state.showWifiForm = true;
            
            this.notification.add(`Camera found: ${device.name}`, {
                type: "success",
            });
        } catch (error) {
            this.state.status = 'error';
            this.state.statusMessage = error.message;
            this.notification.add(error.message, { type: "danger" });
        }
    }
    
    /**
     * Provision the camera with WiFi credentials
     */
    async provisionWifi() {
        if (!this.state.ssid || !this.state.password) {
            this.notification.add("Please enter WiFi SSID and password", { type: "warning" });
            return;
        }
        
        this.state.isProvisioning = true;
        this.state.status = 'connecting';
        this.state.statusMessage = 'Connecting to camera...';
        
        try {
            // Connect to camera
            await this.manager.connect();
            this.state.statusMessage = 'Connected! Sending WiFi credentials...';
            
            // Set up notification handler
            this.manager.onStatusUpdate = (status, message) => {
                this.state.statusMessage = message;
                
                if (status === 0x02 || status === 'connected') {
                    // Connected successfully
                    this.state.status = 'success';
                    this.notification.add("Camera connected to WiFi successfully!", { type: "success" });
                    this.saveCamera();
                } else if (status === 0x03 || status === 0x04 || status === 0x05) {
                    // Error
                    this.state.status = 'error';
                    this.notification.add(message, { type: "danger" });
                }
            };
            
            // Send credentials
            await this.manager.sendWiFiCredentials(this.state.ssid, this.state.password);
            this.state.statusMessage = 'Credentials sent! Waiting for camera to connect to WiFi...';
            
            // Wait for notification or timeout after 60 seconds
            setTimeout(() => {
                if (this.state.status === 'connecting') {
                    this.state.status = 'success';
                    this.state.statusMessage = 'Setup complete! Camera should now be connected.';
                    this.saveCamera();
                }
            }, 60000);
            
        } catch (error) {
            this.state.status = 'error';
            this.state.statusMessage = error.message;
            this.notification.add(error.message, { type: "danger" });
        } finally {
            this.state.isProvisioning = false;
        }
    }
    
    /**
     * Save camera to Odoo database
     */
    async saveCamera() {
        try {
            const cameraId = await this.orm.create("cctv.camera", [{
                name: this.state.device.name || "New Camera",
                mac_address: this.state.device.id,
                wifi_ssid: this.state.ssid,
                wifi_configured: true,
                provisioning_date: new Date().toISOString(),
                state: 'configured',
            }]);
            
            this.notification.add("Camera saved to database!", { type: "success" });
            
            // Navigate to camera form
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "cctv.camera",
                res_id: cameraId,
                views: [[false, "form"]],
            });
        } catch (error) {
            console.error("Error saving camera:", error);
            this.notification.add("Camera provisioned but failed to save: " + error.message, { 
                type: "warning" 
            });
        }
    }
    
    /**
     * Cancel/Reset
     */
    cancel() {
        this.manager.disconnect();
        this.state.status = 'idle';
        this.state.statusMessage = '';
        this.state.device = null;
        this.state.showWifiForm = false;
        this.state.ssid = '';
        this.state.password = '';
    }
}

/**
 * Camera Provision Action Component
 * Used when provisioning from a specific camera record
 */
export class CameraProvisionAction extends Component {
    static template = "camera_provisioning.ProvisionActionTemplate";
    
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        const params = this.props.action?.params || {};
        
        this.state = useState({
            cameraId: params.camera_id,
            ssid: params.wifi_ssid || '',
            password: params.wifi_password || '',
            status: 'ready',
            statusMessage: 'Ready to provision',
        });
        
        this.manager = new BLECameraManager();
        
        onMounted(() => {
            if (this.state.ssid && this.state.password) {
                this.startProvisioning();
            }
        });
    }
    
    async startProvisioning() {
        try {
            const result = await provisionCamera(
                this.state.ssid,
                this.state.password,
                (status, message) => {
                    this.state.status = status;
                    this.state.statusMessage = message;
                }
            );
            
            // Update camera record
            if (this.state.cameraId && result.success) {
                await this.orm.write("cctv.camera", [this.state.cameraId], {
                    mac_address: result.device.id,
                    wifi_ssid: this.state.ssid,
                    wifi_configured: true,
                    provisioning_date: new Date().toISOString(),
                    state: 'configured',
                });
                
                this.notification.add("Camera provisioned successfully!", { type: "success" });
            }
        } catch (error) {
            this.state.status = 'error';
            this.state.statusMessage = error.message;
            this.notification.add(error.message, { type: "danger" });
        }
    }
}

// Register client actions
registry.category("actions").add("camera_ble_scan", CameraBLEScan);
registry.category("actions").add("camera_ble_provision", CameraProvisionAction);

export default { CameraBLEScan, CameraProvisionAction };
