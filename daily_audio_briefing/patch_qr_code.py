
import os

file_path = "/Users/roti/gemini_projects/audio_briefing/daily_audio_briefing/gui_app.py"

correct_show_qr_code_method = """
    def show_qr_code(self, data):
        top = ctk.CTkToplevel(self)
        top.title("Podcast QR Code")
        top.geometry("400x450")
        
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to CTkImage. CTkImage takes PIL Image directly.
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(300, 300))
        
        lbl_img = ctk.CTkLabel(top, image=ctk_img, text="")
        lbl_img.pack(pady=20)
        
        # Fixed f-string: Ensure \n is correctly interpreted
        lbl_text = ctk.CTkLabel(top, text=f"Scan to subscribe:\n{data}", wraplength=380)
        lbl_text.pack(pady=10)
"""

with open(file_path, "r") as f:
    content = f.read()

# Find the start and end of the existing show_qr_code method
start_marker = "    def show_qr_code(self, data):"
end_marker = "    def play_sample(self):"

start_index = content.find(start_marker)
end_index = content.find(end_marker, start_index)

if start_index != -1 and end_index != -1:
    # Replace the old method with the new one
    new_content = content[:start_index] + correct_show_qr_code_method + "
" + content[end_index:]
    with open(file_path, "w") as f:
        f.write(new_content)
    print("Successfully patched show_qr_code method in gui_app.py")
else:
    print("Could not find show_qr_code method or its boundaries. Manual intervention might be needed.")
