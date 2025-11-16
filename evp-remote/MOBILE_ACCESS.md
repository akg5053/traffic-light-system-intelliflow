# Accessing the EVP Remote App from Your Phone

## Quick Fix

The issue is that `localhost` only works on the same computer. To access from your phone:

1. **Make sure your phone and computer are on the same WiFi network**

2. **Restart the Next.js dev server** (it's now configured to listen on all network interfaces):
   ```bash
   # Stop the current server (Ctrl+C)
   # Then restart:
   npm run dev
   ```

3. **Access from your phone using your computer's IP address:**
   ```
   http://10.0.2.15:3000
   ```
   
   ⚠️ **Important:** Replace `10.0.2.15` with your actual computer IP if it's different!

4. **Find your computer's IP address** (if needed):
   - Windows: Open Command Prompt and run `ipconfig`
   - Look for "IPv4 Address" under your active network adapter
   - It should be something like `192.168.x.x` or `10.0.x.x`

5. **Update the API URL** in `.env.local` if your IP changed:
   ```env
   NEXT_PUBLIC_API_URL=http://YOUR_IP_ADDRESS:5000
   ```

## Troubleshooting

- **Can't connect?** Make sure Windows Firewall allows connections on port 3000
- **API not working?** Check that Flask is running and accessible at `http://YOUR_IP:5000/api/evp/state`
- **Still not working?** Try accessing from your computer's browser first: `http://10.0.2.15:3000`

## Note

The IP address `10.0.2.15` might be from a virtual machine or VPN. If you're on a regular WiFi network, your IP is likely `192.168.x.x`. Check with `ipconfig` to be sure!

