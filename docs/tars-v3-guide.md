# TARS-AI V3 build guide (backup copy)

> Text of the [TARS-AI V3 wiki page](https://github.com/TARS-AI-Community/TARS-AI/wiki/V3)
> (wiki commit `168f819`, May 2026), saved here in case the original goes away.
> By the TARS-AI Community, CC-BY-NC 4.0. **The photos are not included**: the image links
> still point to GitHub and would break with the original. To keep the photos too, open the
> wiki page on your PC and use Print → Save as PDF.
>
> Where this guide runs `app-servotester.py`, use `python3 -m tars.calibrate preset` instead
> (see `pi/README.md`). Their software setup sections are for their app, not ours.

---

<p align="center">
    <a href="https://discord.gg/AmE2Gv9EUt">
      <img alt="Discord Invitation Link" src="https://img.shields.io/discord/1311295890182508605" align="center" />
    </a>
</p>

Current OS: Amelia

🚨 Note: Always disconnect the Raspberry pi from power source before connecting wires to it.

# 📋 Bill of Materials

> **Important Notes:**
> - ⚠️ **USB CONNECTION - CHOOSE ONE:** The USB C breakout board is recommended (takes less space, carries more current) but requires soldering. The USB cable is easier (no soldering) but takes more space.
> - 🦾 **ARM BUILD:** Components marked "(only if building the arms)" are required only for the full build with arms
> - ⚡ **SOLDERING REQUIRED:** USB C breakout board and INA260 battery sensor require soldering
> - **Speakers:** Check if speakers are already included with your USB sound card before purchasing separately. (They are with the link below)
> - Before buying something else, it is recommended to ask first in the corresponding discord channel.
> - If you source your screws yourself instead of using the kits, make sure you use **flat head screws**, it does not matter if they are type hex or torx
 or phillips.
<img width="480" height="218" alt="image" src="https://github.com/user-attachments/assets/b3a79ff9-8b90-4d45-8f15-e017cfac118e" />


### Build Configuration Summary
- **Basic Build (No Arms):** Skip components marked "(only if building the arms)" - you'll need 4 MG996R servos and 1 kit of M3 screws
- **Full Build (With Arms):** Include all components - you'll need 6 MG996R servos, 4 MG90s servos, 6 servo extension cables, 4 magnets, and 2 kits of M3 screws
- 2 screw Kits is more than actually required for the build with arms but I guess they will serve for other projects. I will add a complete list with totals soon if anyone want to purchase exactly what is required.
- **⚠️ Important:** The arm version can be built at a later time, but it is strongly suggested to install the extension cables during the initial build so that you do not have to disassemble anything when ready to add them.
- There are 2 different screen supports (one 1024x600 and one 800x480). Print the one required for the screen you have bought.
<table border="1" cellpadding="8" cellspacing="0">
<thead>
<tr bgcolor="#4CAF50">
<th><font color="white">Category</font></th>
<th><font color="white">Component</font></th>
<th><font color="white">Description</font></th>
<th><font color="white">Quantity</font></th>
<th><font color="white">Link</font></th>
</tr>
</thead>
<tbody>

<!-- 3D Printing -->
<tr>
<td rowspan="4" bgcolor="#e8e8e8"><strong>3D Printing</strong></td>
<td>3D Printer</td>
<td>Any printer will do as long as the bed is at least 180x180</td>
<td>—</td>
<td>—</td>
</tr>
<tr>
<td>PETG Filament <strong><font color="#d32f2f">(RECOMMENDED)</font></strong></td>
<td>Rigid components</td>
<td>1kg (1.5kg for the arm version)</td>
<td>—</td>
</tr>
<tr>
<td>PLA Filament <strong><font color="#d32f2f">(ALTERNATIVE)</font></strong></td>
<td>Rigid components. Cheaper and less durable</td>
<td>1kg</td>
<td>—</td>
</tr>
<tr>
<td>TPU Filament <strong><font color="#388e3c">(OPTIONAL)</font></strong></td>
<td>For the foot pads</td>
<td>200g</td>
<td>—</td>
</tr>

<!-- Core Components -->
<tr>
<td rowspan="2" bgcolor="#e8e8e8"><strong>Core Components</strong></td>
<td>Raspberry Pi 5 (4GB+ RAM) (8GB recommended)</td>
<td>Main computing unit</td>
<td>1</td>
<td><a href="https://www.amazon.com/Raspberry-Pi-8GB-SC1112-Quad-core/dp/B0CK2FCG1K" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>Raspberry Pi 5 Active Cooler</td>
<td>Fan and Heat Sink for Pi</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B0CLXZBR5P" target="_blank">(Buy)</a></td>
</tr>

<!-- Display -->
<tr>
<td rowspan="4" bgcolor="#e8e8e8"><strong>Display</strong></td>
<td bgcolor="#fff3cd"><strong>5" 1024x600 UeeKKoo DSI Display ⚠️ CHOOSE ONE</strong></td>
<td><strong>Higher resolution display option</strong></td>
<td>1 – (1 needed)</td>
<td><a href="https://www.amazon.com/dp/B0DDTSZ5PQ" target="_blank">(Buy)</a></td>
</tr>

<tr>
<td bgcolor="#fff3cd"><strong>5" 800x480 Hosyond DSI Display ⚠️ CHOOSE ONE</strong></td>
<td><strong>Standard resolution display option</strong></td>
<td>1 – (1 needed)</td>
<td><a href="https://www.amazon.com/dp/B0CXTFN8K9" target="_blank">(Buy)</a></td>
</tr>

<tr>
<td bgcolor="#fff3cd"><strong>5" 800x480 Waveshare DSI Display ⚠️ CHOOSE ONE</strong></td>
<td><strong>Standard resolution display option</strong></td>
<td>1 – (1 needed)</td>
<td><a href="https://www.amazon.com/dp/B08H23KB1G" target="_blank">(Buy)</a></td>
</tr>

<tr>
<td>200mm DSI Ribbon Cable <strong><font color="#388e3c">(OPTIONAL)</font></strong></td>
<td>Prevents having to fold the cable that comes with the screen</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B0D12N6TLW" target="_blank">(Buy)</a></td>
</tr>

<!-- Power Components -->
<tr>
<td rowspan="9" bgcolor="#e8e8e8"><strong>Power Components</strong></td>
<td>12V Rechargeable Li-ion Battery 3000 mAh with Charger</td>
<td>Main power supply</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B0DF7T3LG1" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>XL4015E DC 5A Adjustable Buck Converter</td>
<td>Step-down converter for the servos (12V to 6V)</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B085T73CSD" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>DC 6A USB Voltage Regulator</td>
<td>Step-down converter for the Pi (12V to 5V, 5A)</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B07X5H4M42/" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>Micro Rocker Switch</td>
<td>Power switch</td>
<td>1 – (1 needed)</td>
<td><a href="https://www.amazon.com/dp/B07Y1GDRQG" target="_blank">(Buy)</a></td>
</tr>
<tr bgcolor="#fff3cd">
<td><strong>USB Cable ⚠️ CHOOSE ONE</strong></td>
<td><strong>Power connection for the Pi. Easy option (no soldering required) but takes more space</strong></td>
<td>1 – (1 needed)</td>
<td><a href="https://www.amazon.com/dp/B0DPF8TFC9" target="_blank">(Buy)</a></td>
</tr>
<tr bgcolor="#fff3cd">
<td><strong>USB C Male Breakout Board ⚠️ CHOOSE ONE</strong></td>
<td><strong>Power connection for the Pi. Better option (takes less space, carries more current) but requires soldering ⚡</strong></td>
<td>1 – (1 needed)</td>
<td><a href="https://www.amazon.com/dp/B0D9W8B97B" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>40cm Dupont Cables (Female to Female)</td>
<td>Connection cables for INA260 and PCA9685</td>
<td>1 – (8 needed)</td>
<td><a href="https://www.amazon.com/dp/B07GCZV4BS" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>20 Gauge 2 Conductor Parallel Wire</td>
<td>Parallel power wiring (~200cm)</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B0B9JCXN9M" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>INA260 Battery Sensor <strong><font color="#388e3c">(OPTIONAL)</font></strong></td>
<td>Battery monitoring (requires soldering ⚡)</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B07S8QYDF8" target="_blank">(Buy)</a></td>
</tr>

<!-- Servo -->
<tr>
<td rowspan="4" bgcolor="#e8e8e8"><strong>Servo</strong></td>
<td>PCA9685 16-Channel PWM/Servo Driver</td>
<td>I2C interface for servo control</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B07BRS249H" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>MG996R Servos</td>
<td>Main servo (180 degree)</td>
<td>1 – (4 needed (or 6 if building the arms))</td>
<td><a href="https://www.amazon.com/dp/B0D7M2Y2BR" target="_blank">(Buy)</a></td>
</tr>
<tr bgcolor="#e3f2fd">
<td><strong>MG90S Servos (only if building the arms)</strong></td>
<td>Servos for the forearms and hands</td>
<td>1 – (4 needed if building the arms)</td>
<td><a href="https://www.amazon.com/dp/B0CP98TZJ2" target="_blank">(Buy)</a></td>
</tr>
<tr bgcolor="#e3f2fd">
<td><strong>12" Servo Extension Cables (Male to Female) (only if building the arms)</strong></td>
<td>Extension cables for the servos</td>
<td>1 - (6 needed if building the arms)</td>
<td><a href="https://www.amazon.com/dp/B0983HX952" target="_blank">(Buy)</a></td>
</tr>

<!-- Audio System -->
<tr>
<td rowspan="2" bgcolor="#e8e8e8"><strong>Audio System</strong></td>
<td>USB Sound Card</td>
<td>Audio input and output board</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B0CN1C1VPR" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>8Ω 5W Speaker</td>
<td>Audio output (if they do not already come with the USB sound card)</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B082XDM9J3" target="_blank">(Buy)</a></td>
</tr>

<!-- Camera System -->
<tr>
<td bgcolor="#e8e8e8"><strong>Camera System</strong></td>
<td>OV5647 5MP Camera Module</td>
<td>Visual input</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B08Q34FKFY" target="_blank">(Buy)</a></td>
</tr>

<!-- Hardware -->
<tr>
<td rowspan="5" bgcolor="#e8e8e8"><strong>Hardware</strong></td>
<td><strong>10x3mm Magnets (only if building the arms)</strong></td>
<td>For magnetic attachments</td>
<td>1 – (4 needed)</td>
<td><a href="https://www.amazon.com/dp/B0BVY5VYQY" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>6" Velcro Straps</td>
<td>Cable management</td>
<td>1 – (2 needed)</td>
<td><a href="https://www.amazon.com/dp/B081HH5X61" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>Heat Shrink Tubing</td>
<td>For securing wires</td>
<td>1</td>
<td><a href="https://www.amazon.com/dp/B01MFA3OFA" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>Spade Connectors</td>
<td>For connecting the switch</td>
<td>1 - (2 needed)</td>
<td><a href="https://www.amazon.com/dp/B0FPQ3YS6M" target="_blank">(Buy)</a></td>
</tr>
<tr>
<td>M3 Screws</td>
<td>M3 screws, different sizes used</td>
<td>1 kit or 2 if building the arms</td>
<td><a href="https://www.amazon.com/dp/B0B38GL3F8" target="_blank">(Buy)</a></td>
</tr>

</tbody>
</table>


# 🔩 Screw Count by Build Type

BUILD WITHOUT ARMS (Legs Only)

| Screw Type | Quantity Needed | Notes |
|------------|----------------|-------|
| **M3x5mm** | **17** | Electronics, camera, audio, servo controller |
| **M3x8mm** | **15** | Electronics, torso assembly, speakers |
| **M3x10mm** | **12** | Chassis connectors |
| **M3x12mm** | **16** | Lids and covers |
| **M3x16mm** | **12** | Bottom assembly, leg-to-hull connection |
| **M3x18mm** | **12** | Leg mount, servo clips |
| **M3x20mm** | **18** | Servo mounting and hull assembly |
| **M3x35mm** | **4** | Leg mount assembly channels |
| **Self-tapping screws** | **6-7** | *Included with MG996R servos* (PCA9685, servo horns, optional INA260) |
| **M2.5 screws** | **2** | *Included with screen* (Screen mounting) |

**Total M3 screws needed: ~116**

---

BUILD WITH ARMS (Full Build)

| Screw Type | Quantity Needed | Notes |
|------------|----------------|-------|
| **M3x5mm** | **17** | Electronics, camera, audio, servo controller |
| **M3x8mm** | **35** | Electronics, torso, speakers, fingers, arm lids |
| **M3x10mm** | **14** | Chassis connectors, forearm pushers |
| **M3x12mm** | **28** | Lids, arm servos, arm shaft assemblies |
| **M3x16mm** | **12** | Bottom assembly, leg-to-hull connection |
| **M3x18mm** | **12** | Leg mount, servo clips |
| **M3x20mm** | **18** | Servo mounting and hull assembly |
| **M3x35mm** | **4** | Leg mount assembly channels |
| **Self-tapping screws** | **14-15** | *Included with MG996R & MG90s servos* (PCA9685, all servo horns, optional INA260) |
| **M2.5 screws** | **6** | *Included with screen (2) & MG90s servos (4)* (Screen mounting, forearm & hand servo horns) |

**Total M3 screws needed: ~140**

---

# 🖨️ 3D Printing Guide

- **Layer height:** 0.2 mm  
- **Minimum walls:** 3  
- **Infill:** 20 (Gyroid)
- **Top / Bottom layers:** 5  
- Don't use any Brim
- Enable **automatic Tree supports** for all parts
  (Some areas require supports but can be hard to spot in the slicer preview.)
- **Support Threshold Angle:** 10 (Avoid having supports in the screw holes)
- All parts are **pre-oriented**.  
  It is strongly recommended to keep the same orientation and rotation, as the final aesthetics depend on it.
- Print the **calibration guide** first to verify your printer tolerances.  
  All parts are designed with additional clearance to accommodate up to **±0.02 mm** dimensional deviation.

[3D Parts](https://github.com/TARS-AI-Community/TARS-AI/tree/V3/3d%20Printer%20Files)

---

# 🔌 Electronics Assembly

## Step 1: Install Core Components

![Switch Installation](https://github.com/user-attachments/assets/d2f7a7fe-679d-4a48-aed6-a76975540abf)

- Push the switch in the space made for it in the Buck Converter Support part.
- If using an INA260 (Battery % monitor), secure it to the side of the Buck Converter Support using **1 self-tapping screw** (You should have some that came in with the MG996R servo).

![Buck Converter Installation](https://github.com/user-attachments/assets/3f8b2b19-1d2d-44fd-8f32-40f603dbfd50)

- Connect a **35cm length of wire** to the out poles of the Buck Converter used for the servo.
- Using **3 M3x5mm screws** (identified by the red arrow), attach the 2 buck converters in the same orientation shown in the picture. 
- Use the Buck Converter Bracket part to hold the buck converter used by the Raspberry Pi.

---

## Step 2: Wire Power Connections and Adjust Voltage

![Power Wiring Diagram](https://github.com/user-attachments/assets/d5035c8d-0da2-4394-b67a-298a020e1e09)

Power cable wiring diagram. Following this diagram, use **20AWG wire** to link everything. Keep the wires short to the components within the support, you can have a longer length going to the battery (15cm max).

![Completed Wiring](https://github.com/user-attachments/assets/4f4a4a7c-350c-46f9-a7bd-2f17afffc533)

It should look like this once completed.

![Battery Charger Installation](https://github.com/user-attachments/assets/e0416d14-3c56-45a9-9513-dcc0c3243c87)

- Insert the Battery charger plug in the support and use an **M3x8mm screw** to hold it in place.

![Voltage Adjustment](https://github.com/user-attachments/assets/696ccf03-638e-4afb-b05b-30d2193e9819)

- Connect the Battery and turn the power ON. 
- Using a small screwdriver, turn the screw to adjust the buck converter to output **6.2V** (It might take several turns before you see a change).

---

## Step 3: Install Raspberry Pi

![Raspberry Pi Mounting](https://github.com/user-attachments/assets/3453467b-cbbd-4a62-b642-c5f9b9acc1c8)

- Place the Raspberry Pi on its support and use **2 M3x8mm screws** and the Raspberry Pi Support Bracket to hold it in place.

![Raspberry Pi Assembly](https://github.com/user-attachments/assets/7289d7d4-6073-4a92-90e7-4f57d1622515)

- Place the Raspberry Pi and support on top of the buck converter assembly and secure it in place using **2 M3x5mm screws**.

---

## Step 4: Create Wire Loom and Final Connections

![Wire Loom Diagram](https://github.com/user-attachments/assets/07419257-c52f-4756-88c1-c4b5f524a435)

- Create the wire loom to connect the PCA9685 and the INA260 (if using) to the Raspberry Pi following this schema. 
- Use about **35cm of wire length** for the wires going to the PCA9685. 
- You can use **22AWG or 24AWG wire** for this if making your own wire loom with dupont connectors, otherwise use **30cm premade dupont connector** (and splice the wire if you are using an INA260).

**At this stage, the electronics setup is complete** and you should be able to power the Raspberry Pi, the Servo Controller (PCA9685) and the INA260 (if using). You can keep the charger plugged in while everything is powered on, it will charge the battery at the same time as providing enough power for the computer.

---

# 🔊 Screen, Camera and Audio

## Step 1: Install USB Audio Board and Battery

![USB Audio Board Installation](https://github.com/user-attachments/assets/2445bb0c-04f0-4e86-a4d6-809a9eea1b2a)

- Remove the top plastic casing on the USB to AUDIO board, use something to pry it open, it's only a press fit casing.
- Install it on the Lower Chassis Lid using the Soundcard Brace and **2 M3x5mm screws**
- Using Velcro Straps, install the Battery on the Chassis Lid in the orientation shown
- If the Velcro Straps are too long, you can cut them

---

## Step 2: Install Camera

![Camera Installation](https://github.com/user-attachments/assets/334d266d-e508-41e8-891b-126f198058c9)

- Using **2 M3x5mm screws**, install the camera to the Upper Lid 5inch

---

## Step 3: Install Screen

![Screen Installation](https://github.com/user-attachments/assets/91f445e2-523c-44fe-b50a-353b49527f63)

- Secure the screen to the Screen Support using the screws that came with the Screen kit.

![Lid Installation](https://github.com/user-attachments/assets/2e52ef4d-7671-4c6c-b1a7-1c4b80d39d3e)

- Install the support and screen on the Upper Lid 5inch using **4 M3x5mm screws**

---

## Step 4: Connect Screen and Camera to Raspberry Pi

![DSI Connection Diagram](https://github.com/user-attachments/assets/0cef9750-a301-4eae-a612-0613985373a6)

- When needed, connect the Screen and Camera to the DSI Connectors on the Raspberry Pi (Be gentle with these connectors, they are easy to break):
  - **CAM/DSI 0** = Screen
  - **CAM/DSI 1** = Camera

---

# 💻 Raspberry Pi OS Installation

## What You'll Need

- **Raspberry Pi 5**
- **Active Cooler**
- **microSD card** (32 GB minimum, 64 GB+ recommended)
- **microSD card reader** for your computer
- **Keyboard and mouse** (Optional, you can SSH, or VNC *)
- **HDMI cable + Micro HDMI adapter + monitor** (Optional, we can use the screen we installed above or you can use VNC *)
- **USB-C power supply** (27 W official recommended, Optional, the electronics section shows how you can power the Raspberry Pi)

(* Refer to the How To section on how to SSH or use VNC)

Before anything else, install the active cooler on the raspberry pi. Connecting to a monitor is optional if you know how to SSH to do all of the rest of the installation.

---

## Step 1: Download Raspberry Pi Imager

1. Go to the official Raspberry Pi site:  
   🔗 [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)
2. Download and install **Raspberry Pi Imager** for your operating system (Windows, macOS, or Ubuntu).

---

## Step 2: Flash Raspberry Pi OS to the microSD Card

1. Launch **Raspberry Pi Imager**.
2. Click **"Choose Device"** → select **Raspberry Pi 5**.
3. Click **"Choose OS"** → select `Raspberry Pi OS (64-bit)` (Use Trixie)
4. Click **"Choose Storage"** → select your microSD card.
5. Click the ⚙️ **settings icon** (bottom right) to open **advanced settings**:
   - Enable **SSH** (optional, for remote access)
   - Set a **hostname**
   - Configure **Wi-Fi** (SSID, password, country)
   - Set a **username and password**
   - Choose **locale/time zone/keyboard layout**
6. Click **Save** → then **Write**.  
   Wait a few minutes for the flashing process to complete.

---

## Step 3: Modify the config.txt File for DSI Display

- After flashing is complete, open the boot partition on your SD card (should show up as a drive in File Explorer).
- Open the file: `config.txt`.
- Scroll to the bottom and add the following lines:

```
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dsi-waveshare-panel,7_0_inchC,dsi0
```

**NOTE:** You may already have the "dtoverlay=vc4-kms-v3d" line in your config.txt. In that case, you DO NOT need to add it again.

- Save the file.
- Right-click the SD card and choose Eject.

---

## Step 4: Boot the Raspberry Pi 5

1. Insert the **microSD card** into your Raspberry Pi 5.
2. Connect the **monitor**, **keyboard**, **mouse**.
3. Connect the **power cable**

---

## Step 5: Update the System

Once you reach the desktop or connect via SSH, open a terminal and run:

```bash 
sudo apt update && sudo apt full-upgrade -y 
sudo reboot
```

This ensures you're running the latest kernel and firmware optimized for Raspberry Pi 5.

---

## Step 6: Enable Interfaces

If you need to enable interfaces like camera, I2C, or SPI, run:

```bash
sudo raspi-config
```

Then navigate to Enable the Camera, I2C, SPI, VNC.

---

# 🧠 TARS Software Installation

* [It is recommended to use VNC do do these steps](./*-How-to#%EF%B8%8F-connecting-to-rpi-via-vnc)

## Step 1: Clone the TARS-AI Repository

1. Open a terminal on your Raspberry Pi.
2. Install Python venv (if not already installed) and clone the repository:

```console
sudo apt install python3-venv -y
```

```bash
git clone -b V3 https://github.com/TARS-AI-Community/TARS-AI
```

3. Navigate to the cloned directory:

```bash
cd TARS-AI
```

4. Update script permissions:

```bash
chmod 777 Install.sh
```

5. Allow the script to be executable:

```bash
chmod a+x Install.sh
```

6. Run the installation:

```bash
./Install.sh
```

---

## Step 2: Configure API Keys

To enable **LLM** and **TTS** functionality, you need to configure your API keys.

- Open the `.env` file in the TARS-AI folder in a text editor and replace the placeholders with your valid API keys:

```bash
sudo nano .env
```

- **Get Your API Keys**

  **Required:**
  - [[OpenAI API Key](https://www.youtube.com/watch?v=OB99E7Y1cMA)](https://www.youtube.com/watch?v=OB99E7Y1cMA)

  **Recommended:**
  - [[Elevenlabs API Key](https://elevenlabs.io/app/developers/api-keys)](https://elevenlabs.io/app/developers/api-keys)
  - [[Picovoice](https://picovoice.ai/)](https://picovoice.ai)

OpenAI is not free but it is also not expensive, Elevenlabs has a free tier and usually is enough for normal use, there are other free options in the software that can be used for free too.

---

## Step 3: Configure the Program

- From the TARS-AI folder, navigate to the software source directory:

```bash
cd src/
```

- Open the `config.ini` file in the TARS-AI\src folder in a text editor and edit the options.

```bash
sudo nano config.ini
```

---

## Step 4: Run the Program

- From the TARS-AI folder:

```bash
./tars-launcher.sh
```

Or

- From the TARS-AI folder, Navigate to the software source directory:

```bash
cd src/
```

- Activate the Virtual Environment, the virtual environment must be activated each time you want to start the program:

```bash
source .venv/bin/activate
```

- You should now see `(.venv)` in your terminal shell prompt:
- Start the TARS-AI assistant:

```bash
python app.py
```

Note that while the program will run if there was no errors in the previous steps, a microphone and a way to output sound is required to interact with it. For now, you can use an USB microphone and something like bluetooth speakers if you want to test the Software while you are building the rest of the Robot.

---

# 📦 Torso Assembly

## Step 1: Install Power Door

![Power Door Installation](https://github.com/user-attachments/assets/51ac01d1-970d-4d0b-bc45-80a6eb550dd2)

Install the power door using some length of filament. Make sure to push the filament completely through the hole on both sides of the case. Cut any filament that might be protruding from the hole.

---

## Step 2: Assemble Main Chassis and Speaker Modules

![Chassis Connection](https://github.com/user-attachments/assets/52209211-f8b2-4e73-859a-7f4d174a7b60)

Connect the Lower Chassis to the Upper Chassis using the middle, left and right Chassis Connectors and **12 M3x10mm screws**.

![Speaker Module Installation](https://github.com/user-attachments/assets/bed208ef-f5ec-43e2-a27b-fb76558dd940)

Pass each speaker module through the side opening in the Upper Chassis, ensuring that enough wire is pulled through on each side.

---

## Step 3: Build and Install Leg Mount Assemblies

![Leg Mount Assembly](https://github.com/user-attachments/assets/b78bce82-e112-4daf-8f17-f18387f3d127)

Assemble the Left and Right leg mount assembly using **2 M3x35mm screws** on each side to link the Channel, Pusher, Pusher Guide and Shaft. 

**Important:** 
- Each assembly should slide easily without having any play
- The pusher guide should also move freely
- The left and right assembly should mirror each other

![Assembly Attachment](https://github.com/user-attachments/assets/28097d1a-5900-480b-ba3a-3727c20dbcf6)

Using **8 M3x18mm screws**, attach the Left and Right assembly. Make sure the audio wire goes in the hole of the assembly on each side - this is where all wires are going to be channeled to each leg.

---

## Step 4: Position Main Servos and Route Wiring

![Main Servo Arrangement](https://github.com/user-attachments/assets/cc1d87e1-77df-4ae0-ab5e-097b296a12a7)

Arrange all 4 main **MG996R servos** as shown in the image. The number on each one corresponds to the pin ID they will be connected to on the servo controller. Servo 2 and 3 wires need to go through the Left and Right holes where the audio wires are going through.

![Extension Servo Wires](https://github.com/user-attachments/assets/cec3737e-7820-4ef6-8366-3dd5f3a6b855)

**For Arms Version builders only:** Feed the extension servo wires through the Left and Right holes and identify them for later (tape and marker works well).

- **Left side:** 3 wires for pins 4, 5, 6
- **Right side:** 3 wires for pins 7, 8, 9

> If you are not building the Arms version, you can skip the extension wires.

---

## Step 5: Install Servo Controller and Electronic Support

![Servo Controller Installation](https://github.com/user-attachments/assets/ec507407-8479-4298-b806-f48494a50f73)

1. Secure the **PCA9685 board** to the Servo Controller Support using **2 self-tapping screws** (included with MG996R servo)
2. Feed the wires through the middle hole and out of the top hole so they are not in the way of the left and right assembly
3. Connect the wires to the corresponding pins on the PCA9685
4. Pull all wire slack out of the main torso (there is more than enough room in the leg for extra length)
5. Secure the servo controller support on the Upper Chassis using **4 M3x5mm screws**

![Assembled Servo Controller](https://github.com/user-attachments/assets/ee33efbf-9f10-4c88-a931-f9e43193262f)

![Electronic Support](https://github.com/user-attachments/assets/7ed3bff4-77e0-48f1-810c-61a8b7f89503)

Using **4 M3x8mm screws**, secure the electronic support to the Lower Chassis. Once everything is in place, it should look like the images above.

---

## Step 6: Install Servo Horns and Hull Hubs

![Servo Horn Attachment](https://github.com/user-attachments/assets/7fe1b8c5-aff8-4a94-bedb-59734cb6faeb)

Using **4 self-tapping screws** and **2 servo horns with 2 prongs** (included with MG996R servo), attach them to the left and right servo connectors.

![Hull Hub Installation](https://github.com/user-attachments/assets/56e20130-eb83-469c-ae07-4cf71db08f55)

Slide the left and right Hull Hub on both sides. **Important:** They can only be installed at this step, so make sure the orientation matches the image.

---

## Step 7: Set Initial Servo Positions

![Initial Position Setup](https://github.com/user-attachments/assets/c181ebf9-9d35-428e-8362-6e15ceb170cf)

At this point, all electronics should be working on battery power. We will now set the initial position of the servos and assemble them in place.

**Navigate to the servo tester app:**

```bash
cd TARS-AI
cd src
source .venv/bin/activate
python app-servotester.py
```
**Choose option 2:** Terminal Mode (text-based)

**Run Command 1:** Set all servos to preset position

> **Warning:** The servos will remain under power while we add components. While they will try to keep their position, it is important to avoid forcing them to move. We can adjust minor misalignment later.

![Servo Connector Positioning](https://github.com/user-attachments/assets/3370ac38-ac01-4984-8b4a-9a28a7f70f2a)

Position the assembled Servo Connector so the servo horn is parallel to the servo as much as possible. Each servo is slightly different, so it might not line up exactly, but we can fix this later. Do this for both Left and Right sides and use the **M3 screw** (included with servo) to secure in place.

---

## Step 8: Prepare and Install Modified Servo Horns

![Modified Servo Horn](https://github.com/user-attachments/assets/20c9f896-d1a0-4cc6-ac5a-19e7ebbf9c45)

Cut one side of **2 servo horns with 2 prongs** (included with MG996R servo).

![Torso Servo Horn Installation](https://github.com/user-attachments/assets/e67e2ae3-5897-4abf-a545-cb8764c48212)

Position the modified horns on the Torso servos at a **90-degree angle**. If it's not exactly 90 degrees, we can adjust the minor difference later. Do this for both sides - they should mirror each other.

![Servo Connector Arm Attachment](https://github.com/user-attachments/assets/310fe6b9-8118-4de0-8c2f-b3866db4ca2e)

Put the Servo Connector Arm on top of each side and use **2 M3x8mm screws** to secure everything in place.

**At this stage, you can disable power to the servos using the script:**

**Run Command 2:** Disable all servos

---

## Step 9: Final Servo Mounting

![Servo Mounting](https://github.com/user-attachments/assets/79c3c752-8608-41dd-bef9-e00f47813b0d)

Using **4 M3x20mm screws**, attach the left and right servos to the leg mount. **Note:** The screws go in at an angle.

![Final Assembly](https://github.com/user-attachments/assets/cbd2b674-eae1-45a8-b3ff-6c627a23a20c)

Using **2 M3x20mm screws**, attach the servo connector arm on the Pusher. **Important:** Make sure it's not too tight. Do this for both sides and position the servos back in place in the case.

![Torso Servo Clips](https://github.com/user-attachments/assets/5c0c2b41-8d54-49c2-a645-2c24f37840a8)

Use **4 M3x18mm screws** to bolt down the left and right Torso Servo Clip. I am also using a small tie-wrap to bundle the wires together here so they do not get caught in the mechanism.

---

## Step 10: Install USB Cable and Chassis Lids

![USB Cable Management](https://github.com/user-attachments/assets/d70b12a2-b182-4780-a777-0ebc25ccf478)

The USB cable for the Audio Card is a bit bulky so fold it and attach it with some tie-wrap in order for it to use less space in the case and be out of the way of the mechanism.

---

## Step 11: Secure Chassis and Install Base

![Chassis Assembly](https://github.com/user-attachments/assets/831251e0-be64-417f-8b95-fc74aa6605b7)

- Use **4 M3x12mm screws** to secure the top and lower lids (red arrows)
- Use **4 M3x16mm screws** to assemble the bottom footpad and base to the lower chassis

---

## Step 12: Install Hull and Leg Components

![Hull Installation](https://github.com/user-attachments/assets/53b91d77-eb05-4b79-accf-00f67f38f85e)

- Place the leg spacer (identified by the blue arrow) between the case and the Hull part
- Using **2 M3x20mm screws**, first secure the Hull Hub to the Hull part
- Then bolt the servo clip over the servo using **3 M3x20mm screws**
- Do the same thing for both sides (Left and Right)

---

## Step 13: Install Hull Lid

![Hull Lid Installation](https://github.com/user-attachments/assets/62ee5e1c-339a-4cf8-8d81-51b7bafc4c18)

Install the Hull Lid using **4 M3x12mm screws**.

---


# 🦿 Legs (No Arm Version)

## Step 1: Install Speakers on Lower Leg Lid

![Speaker Installation](https://github.com/user-attachments/assets/e4ad1556-d2f4-431d-b523-6a196aae46a1)

Place the speakers on the Lower Leg Lid and set it in place using **2 M3x8mm screws**. Do the same thing for the other side.

---

## Step 2: Install Footpad

![Footpad Installation](https://github.com/user-attachments/assets/962bc082-eede-492d-8c56-b1cb0095338d)

Slide the foot pad on the lower leg case. Do the same thing for the other side.

---

## Step 3: Attach Lower Leg Lid

![Lower Leg Lid Installation](https://github.com/user-attachments/assets/13a036c1-5bde-4c6a-a36d-23203d9c3ee6)

Place the Lid on the Lower Leg Case and secure it using **4 M3x12mm screws**. Do the same thing for the other side.

---

## Step 4: Join Lower Leg to Hull

![Lower Leg to Hull Connection](https://github.com/user-attachments/assets/7bb67158-61fd-41f4-b66e-6bef17c19d01)

Join the Lower Leg to the Hull using **4 M3x16mm screws**. Do the same for the other side.


---

# 🦾 Legs with Arms

Note: This is using the left leg parts, the right leg mirrors the left one.

## Step 1: Assemble Lower Case

![Lower Case Assembly](https://github.com/user-attachments/assets/96ed5946-d953-468c-82f3-eaaba5a9baaa)

1. Route the speaker assembly into the lower leg case
2. Slide the footpad into the grooves of the lower leg case

![Speaker Installation](https://github.com/user-attachments/assets/35d1af4a-f683-4185-a3f0-5442f2072379)

3. Fix the speaker to the lower case lid using **2 M3x8mm screws**

![Lid Installation](https://github.com/user-attachments/assets/6438af20-ab02-4824-a972-1228ad09982e)

4. Insert the lid on the lower case and bolt it in place using **4 M3x12mm screws**

---

## Step 2: Install Magnets

![Lower Leg Magnet](https://github.com/user-attachments/assets/1c105acf-e7ef-4c22-93fc-a62b3188c4bb)

1. Insert a magnet in the lower leg case, push it firmly in place. It should remain there but if it's too loose, you can add a bit of glue (or hot glue)

![Finger Magnet](https://github.com/user-attachments/assets/6c3de5e4-e5d6-4835-a1b6-a97055c93c0b)

2. Add another magnet in the finger 2 part. Make sure the orientation of the magnet will pull the finger toward the lower leg case. You can use the finger plug to push it in place (add glue if you think it's too loose)

![Magnet Alignment Check](https://github.com/user-attachments/assets/6d364c9f-0c1d-4028-ac78-dc7ce6b902c5)

---

## Step 3: Install Servos

![Main Arm Servo](https://github.com/user-attachments/assets/ba26096f-5fa6-4c45-8429-e87dbbdbc6d4)

1. Add **1 MG90s** to the main arm case, feed the wire through the holes like on the image and secure it with **2 self-tapping screws** that come with the servo

![Forearm Servo](https://github.com/user-attachments/assets/631e12fe-ba61-4cf6-a682-6edc7cec1d22)

2. Add another **MG90s** to the forearm case, feeding the wires through the same holes in the main arm case and use **2 self-tapping screws** to hold it in place

![Finger Rods](https://github.com/user-attachments/assets/523a3c51-fff8-4a57-80ab-ae5b7d910b2b)

3. Install both of the rods on the fingers following this image for the orientation (Finger 1 with Rod 1, Finger 2 with Rod 2), use **2 M3x8mm screws**. The rods should be able to move freely but not have too much slack

![Finger Rods](https://github.com/user-attachments/assets/6ac4f405-7767-4437-a158-72f5078bd10c)

4. Use a length of filament to join the forearm case with both of the fingers

![Forearm Assembly](https://github.com/user-attachments/assets/ace814aa-bd56-465a-a720-b29bfc9131f5)

5. Join the Lower Case with the Main arm case, using the Leg Hinge and **2 lengths of filament**. Make sure the filament goes all the way through the Leg Case as there is a cutout there to allow removal of the filament if needed

![MG996R Installation](https://github.com/user-attachments/assets/20e12c0c-7f46-466f-b8f5-1ea67632906d)

6. Install a **MG996R servo**, oriented like on the image. Make sure the wires from the other servo and speaker go to the sides of the servo so they do not get pinched under. Use **4 M3x12mm screws** to hold it in place

![servo horn](https://github.com/user-attachments/assets/90075731-aec9-4b8a-a29e-aa03f3664fae)

7. Prepare the parts that will extend the main arm. Cut one of the **2 prong servo horns** that came with the MG996R servo, like we did for servo 0 and 1. Use **1 M3x12mm screw** to connect the Leg Arm Shaft and the Leg Arm Pusher - the Arm Shaft should be able to move freely

![Arm Shaft Connection](https://github.com/user-attachments/assets/57622149-254f-4935-96da-18be62531b6a)

8. Use **1 M3x12mm screw** to join the Leg Main Arm Case with the Arm Shaft

---

## Step 4: Connect and Position Servos

Connect the servos to their extensions

**Servo ID's:**
- **Left Arm** (MG996R): 4
- **Left Forearm** (MG90S): 5
- **Left Hand** (MG90S): 6
- **Right Arm** (MG996R): 7
- **Right Forearm** (MG90S): 8
- **Right Hand** (MG90S): 9

Run the app-servotester.py script and set the servos to their preset values:
```bash
cd TARS-AI
cd src
source .venv/bin/activate
python app-servotester.py
```
**Choose option 2:** Terminal Mode (text-based)

**Run Command 1:** Set all servos to preset position

![Servo Attachment](https://github.com/user-attachments/assets/ce28f87c-a3d7-45a0-835f-44a1933860ed)

Keep the servos under power while you connect the arms to them. Don't force the servos to rotate - they are under power so will try to retain their positions. Make sure the cases are oriented like the image, this is the neutral position.

- **Main Arm servo (Blue):** Use the servo horn we cut, place it under the 3D printed Arm Pusher and use **1 M3x8mm screw** to fix on the servo
- **Forearm servo (Red):** Use one of the **1 prong servo horns** that came with the MG90s, place it parallel with the case as much as possible, use the **M2.5 screw** that came with the servo kit to secure it in place. If it's not totally parallel, we can adjust the offsets later
- **Hand servo (Green):** Use **1 M3x10mm screw** to link the Forearm Pusher to the rods and use the **M2.5 screw** that came with the servo kit to fix it in place on the servo

You can now power off the servos using the app-servotester.py:

**Run Command 2:** Disable all servos

---

## Step 5: Install the Lids

![Lid Assembly](https://github.com/user-attachments/assets/c38cb5ff-789f-46a3-afef-7682b5fb9591)

- Use **6 M3x8mm screws** to assemble the Main Arm Lid and the Forearm Lid
- The Leg Upper Lid normally snaps into place but you can add **1 M3x8mm screw** to secure it if you want (the hole is on the side of the case)

---

## Step 6: Join Lower Leg to Hull

![Lower Leg to Hull Connection](https://github.com/user-attachments/assets/7bb67158-61fd-41f4-b66e-6bef17c19d01)

Join the Lower Leg to the Hull using **4 M3x16mm screws**. Do the same for the other side.


# 🎯 Calibration and Offsets

This section is under construction, but the instructions are also located here, in this video: https://www.youtube.com/watch?v=We_4mcOO7hI&t=20s

---

This project is self-funded and built in spare time. If you’d like to help offset hardware and prototyping costs, you can buy me a coffee. Small contributions go a long way toward faster iterations and new features.

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/atomikspace)
