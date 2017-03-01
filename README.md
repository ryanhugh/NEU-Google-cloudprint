# Unfortunately this project no longer works. It worked great for a while and had a bunch of users but then NEU changed something on their end that stopped this from working. :( I am actively interested in finding alternate ways to send print jobs to NEU's servers, so if you hear of something, let me know!

Print to NEU Pharos Printers with Google Cloud print!  

(If you ever get a printer offline error shoot me an email at ryanhughes624@gmail.com and I'll fix it)

## How to use
 1. Send me your @husky.neu.edu email address, and I will share the printer with you.
 2. Accept the invitation for the printer.
 3. Open any page in Google Chrome (New Tab, any PDF, Google Drive document, etc.. ).
 4. Click ctrl-p
 5. Click "Change..." on the left.
 5. Select your @husky.neu.edu email from the drop down in the top right corner.
 6. Select the printer under the section "Google Cloud Print"
 7. Print away!
 8. Wait a couple minutes for your document to be processed.
 9. You will receive an email when the document is ready!

## How it works
 1. When a document is printed, chrome sends a PDF of of the document to Google Cloud Print.
 2. The PDF is downloaded by a python script running on an AWS instance.
 3. The PDF is not stored and is never saved to disk. 
 4. An email is sent to mobileprinting@neu.edu with the PDF and your husky email address.
 5. After northeastern processes the document, it is added to the Pharos print queue. 

Code adapted from https://github.com/armooo/cloudprint
