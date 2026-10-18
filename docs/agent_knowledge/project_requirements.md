# Original Requirements (Project Compass)

Here are the literal requirements from which we started building this system:

> The USB device is needed to protect a Windows application (exe).
> a) We have 5 functions, currently written in C++, that perform simple but secret mathematical calculations.
> b) Each of these functions is about 100 lines of code, so in total, after compilation, it's about 20 KB maximum. These are computationally undemanding functions.
> c) I want to be able to do the following from Python (Windows application):
> - call a selected function on the key (obviously via encrypted communication: windows program -> usb device) to get calculation results.
> - be able to check the 100% true current date and time by retrieving it from the USB device.
> d) Requirements:
> - I don't need to update anything on the key remotely.
> - I want it so that after I save the functions and data, THEY CANNOT BE STOLEN / INSPECTED.
> - I would like these functions to execute in some isolated environment, again so they CANNOT BE STOLEN / INSPECTED.
> - The RTC battery must be physical and secure.
> - I would like it to be impossible to simply clone the contents of the usb device and transfer them to another usb device.
> - I would like the key to block or clear its memory in a situation like a battery disconnection (tampering).
> - I would like there to be as many anti-tampering mechanisms as possible and the code to be 99.9% secure.
> - I don't want to write the security architecture for the USB device code from scratch. I would like most of the security to be Out of the Box, and I just transfer my compiled code, burn what's needed into memory, etc.
> - The device must be able to be mounted in an enclosure similar to a USB flash drive (so max size is feather).
> - The admin must be able to set an expiry date for the license, and the Python app can check if the license is still active.
> - The admin must be able to set the maximum number of users for the app, and the Python app can retrieve how many users are assigned.
> - I want the device to be available for purchase in Poland, generally popular (accessible), and in active production.
