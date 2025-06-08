import json
import requests
import os
import uuid
import websocket
import urllib.parse
import threading
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk
import io
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

class ComfyUIIMageGenerator:
    def __init__(self, server_address="127.0.0.1:8188"):
        """
        Initialize the ComfyUI Image Generator.
        
        Args:
            server_address (str): The address of the ComfyUI server (default: "127.0.0.1:8188")
        """
        if not server_address.startswith(('http://', 'https://')):
            server_address = f"http://{server_address}"
        
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.output_dir = "generated_images"
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_image(self, prompt, negative_prompt="", width=512, height=512, steps=20, cfg=7.5, 
                      sampler_name="euler_ancestral", scheduler="normal"):
        """
        Generate an image using ComfyUI
        
        :param prompt: The positive prompt for image generation
        :param negative_prompt: The negative prompt (things to avoid in the image)
        :param width: Width of the generated image
        :param height: Height of the generated image
        :param steps: Number of diffusion steps
        :param cfg: Classifier Free Guidance scale
        :param sampler_name: Name of the sampler to use
        :param scheduler: Scheduler to use
        :return: Path to the saved image
        """
        # Get the current timestamp for unique node IDs
        timestamp = int(datetime.now().timestamp())
        
        # Create the workflow for SD XL
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": timestamp % (2**32),
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": f"ComfyUI_{timestamp}",
                    "images": ["8", 0]
                }
            }
        }
        
        try:
            # Send the prompt to the server
            print(f"Sending prompt to server at {self.server_address}/prompt...")
            try:
                response = requests.post(
                    f"{self.server_address}/prompt",
                    json={"prompt": workflow, "client_id": self.client_id},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response.raise_for_status()
                
                # Get the prompt ID from the response
                result = response.json()
                if "prompt_id" not in result:
                    print(f"Unexpected response format: {result}")
                    return None
                    
                prompt_id = result["prompt_id"]
                print(f"Prompt queued with ID: {prompt_id}")
                
                # Connect to the WebSocket to monitor progress
                ws_url = f"ws://{self.server_address.replace('http://', '').replace('https://', '')}/ws?clientId={self.client_id}"
                print(f"Connecting to WebSocket at {ws_url}...")
                ws = websocket.WebSocket()
                ws.connect(ws_url)
                
                # Wait for the generation to complete
                print("Waiting for generation to complete...")
                while True:
                    try:
                        out = ws.recv()
                        if isinstance(out, str):
                            message = json.loads(out)
                            if message.get("type") == "status":
                                status = message.get("data", {}).get("status", {})
                                if "exec_info" in status:
                                    remaining = status["exec_info"].get("queue_remaining", 0)
                                    print(f"Status: {remaining} prompts remaining")
                            elif message.get("type") == "executing":
                                data = message.get("data", {})
                                if data.get("node") is None and data.get("prompt_id") == prompt_id:
                                    print("Generation complete!")
                                    break
                    except Exception as e:
                        print(f"WebSocket error: {e}")
                        break
                
                ws.close()
                
                # Get the generated image
                output_path = self.get_generated_image(prompt_id)
                return output_path
                
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            except requests.exceptions.ConnectionError as e:
                print(f"Connection Error: Could not connect to {self.server_address}. Is ComfyUI running?")
            except requests.exceptions.Timeout:
                print("Request timed out. Is the server busy?")
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                return None
            
        except Exception as e:
            print(f"Error during image generation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_generated_image(self, prompt_id):
        """
        Fetch the generated image from the server.
        
        Args:
            prompt_id (str): The ID of the prompt to fetch the image for
            
        Returns:
            str: Path to the saved image, or None if failed
        """
        try:
            # Get the generation history
            hist = requests.get(f"{self.server_address}/history/{prompt_id}").json()
            
            if prompt_id not in hist:
                print(f"No history found for prompt ID: {prompt_id}")
                return None
                
            # Find the output node with images
            for node_id in hist[prompt_id]["outputs"]:
                node_output = hist[prompt_id]["outputs"][node_id]
                if "images" in node_output:
                    for image in node_output["images"]:
                        # Download the image
                        params = urllib.parse.urlencode(image)
                        img_data = requests.get(f"{self.server_address}/view?{params}").content
                        
                        # Ensure output directory exists
                        os.makedirs(self.output_dir, exist_ok=True)
                        
                        # Save the image
                        output_path = os.path.join(self.output_dir, image["filename"])
                        with open(output_path, "wb") as f:
                            f.write(img_data)
                            
                        print(f"Image saved to: {output_path}")
                        return output_path
            
            print("No images found in the generation output")
            return None
            
        except Exception as e:
            print(f"Error fetching generated image: {e}")
            import traceback
            traceback.print_exc()
            return None

class ImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI Image Generator")
        self.root.geometry("800x700")
        
        # Initialize the generator
        self.generator = None
        self.generating = False
        self.current_image = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Server settings
        server_frame = ttk.LabelFrame(main_frame, text="Server Settings", padding="5 5 5 5")
        server_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(server_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.server_var = tk.StringVar(value="127.0.0.1:8188")
        ttk.Entry(server_frame, textvariable=self.server_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(server_frame, text="(default port: 8188)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Prompt
        prompt_frame = ttk.LabelFrame(main_frame, text="Prompt", padding="5 5 5 5")
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(prompt_frame, text="Prompt:").pack(anchor=tk.W, padx=5, pady=2)
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=4, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.prompt_text.insert(tk.END, "a beautiful landscape with mountains and a lake, sunset, 4k, highly detailed")
        
        ttk.Label(prompt_frame, text="Negative Prompt:").pack(anchor=tk.W, padx=5, pady=2)
        self.negative_prompt_text = scrolledtext.ScrolledText(prompt_frame, height=2, wrap=tk.WORD)
        self.negative_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.negative_prompt_text.insert(tk.END, "blurry, low quality, text")
        
        # Parameters
        params_frame = ttk.LabelFrame(main_frame, text="Generation Parameters", padding="5 5 5 5")
        params_frame.pack(fill=tk.X, pady=5)
        
        # Row 1
        ttk.Label(params_frame, text="Width:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.width_var = tk.IntVar(value=768)
        ttk.Spinbox(params_frame, from_=256, to=2048, increment=64, textvariable=self.width_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(params_frame, text="Height:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.height_var = tk.IntVar(value=512)
        ttk.Spinbox(params_frame, from_=256, to=2048, increment=64, textvariable=self.height_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Row 2
        ttk.Label(params_frame, text="Steps:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.steps_var = tk.IntVar(value=20)
        ttk.Spinbox(params_frame, from_=1, to=150, textvariable=self.steps_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(params_frame, text="CFG Scale:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.cfg_var = tk.DoubleVar(value=7.5)
        ttk.Spinbox(params_frame, from_=1.0, to=30.0, increment=0.5, textvariable=self.cfg_var, width=8).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Row 3
        ttk.Label(params_frame, text="Sampler:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.sampler_var = tk.StringVar(value="euler_ancestral")
        ttk.Combobox(params_frame, textvariable=self.sampler_var, values=["euler_ancestral", "euler", "heun", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_2m", "dpmpp_sde", "dpmpp_2m_sde"], width=15).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(params_frame, text="Scheduler:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.scheduler_var = tk.StringVar(value="normal")
        ttk.Combobox(params_frame, textvariable=self.scheduler_var, values=["normal", "karras", "exponential", "simple", "ddim_uniform"], width=15).grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Image display
        self.image_frame = ttk.LabelFrame(main_frame, text="Generated Image", padding="5 5 5 5")
        self.image_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.image_label = ttk.Label(self.image_frame, text="Image will appear here", anchor=tk.CENTER)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate Image", command=self.start_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(button_frame, text="Save Image", command=self.save_image, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Open Output Folder", command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
    
    def start_generation(self):
        if self.generating:
            return
            
        self.generating = True
        self.generate_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.status_var.set("Starting generation...")
        
        # Get values from UI
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        negative_prompt = self.negative_prompt_text.get("1.0", tk.END).strip()
        
        # Start generation in a separate thread
        thread = threading.Thread(target=self.generate_image, args=(
            prompt,
            negative_prompt,
            self.width_var.get(),
            self.height_var.get(),
            self.steps_var.get(),
            self.cfg_var.get(),
            self.sampler_var.get(),
            self.scheduler_var.get()
        ))
        thread.daemon = True
        thread.start()
        
        # Check the thread status
        self.check_thread(thread)
    
    def check_thread(self, thread):
        if thread.is_alive():
            self.root.after(100, lambda: self.check_thread(thread))
        else:
            self.generating = False
            self.generate_btn.config(state=tk.NORMAL)
    
    def generate_image(self, prompt, negative_prompt, width, height, steps, cfg, sampler_name, scheduler):
        try:
            # Initialize the generator with the current server address
            self.generator = ComfyUIIMageGenerator(server_address=self.server_var.get())
            
            # Update status
            self.root.after(0, lambda: self.status_var.set("Generating image..."))
            
            # Generate the image
            output_path = self.generator.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                sampler_name=sampler_name,
                scheduler=scheduler
            )
            
            if output_path:
                # Load and display the image
                self.current_image = Image.open(output_path)
                self.display_image(self.current_image)
                self.save_btn.config(state=tk.NORMAL)
                self.root.after(0, lambda: self.status_var.set(f"Image generated: {output_path}"))
            else:
                self.root.after(0, lambda: self.status_var.set("Failed to generate image"))
                messagebox.showerror("Error", "Failed to generate image. Check the console for details.")
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.status_var.set(f"Error: {error_msg}"))
            messagebox.showerror("Error", f"An error occurred: {error_msg}")
    
    def display_image(self, image):
        # Resize the image to fit in the window while maintaining aspect ratio
        max_size = (700, 500)
        image.thumbnail(max_size, Image.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(image)
        
        # Keep a reference to avoid garbage collection
        self.photo = photo
        
        # Update the image label
        self.image_label.config(image=photo)
        self.image_label.image = photo
    
    def save_image(self):
        if not self.current_image:
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            initialfile=f"generated_{int(datetime.now().timestamp())}.png"
        )
        
        if file_path:
            try:
                self.current_image.save(file_path)
                self.status_var.set(f"Image saved to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")
    
    def open_output_folder(self):
        output_dir = os.path.abspath("generated_images")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        webbrowser.open(f"file://{output_dir}")

def main():
    # Check for required packages
    try:
        import websocket
    except ImportError:
        print("Error: The 'websocket-client' package is required but not installed.")
        print("Please install it using: pip install websocket-client")
        return
    
    # Create and run the application
    root = tk.Tk()
    app = ImageGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
