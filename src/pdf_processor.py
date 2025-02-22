import cv2
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import os

class PDFProcessor:
    def __init__(self):
        self.current_image = None
        self.gridlines = []
        self.rotation_angle = 0
        
    def convert_pdf(self, pdf_file):
        """Convert PDF to list of images"""
        images = convert_from_path(pdf_file)
        return [np.array(img) for img in images]
    
    def get_display_image(self, zoom_level=1.0, gridlines=None, crop_points=None, line_thickness=1):
        """Get image with overlays for display"""
        if self.current_image is None:
            return None
            
        # Convert to PIL Image for processing
        image = Image.fromarray(self.current_image)
        
        # Apply zoom
        if zoom_level != 1.0:
            new_size = (
                int(image.width * zoom_level),
                int(image.height * zoom_level)
            )
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert back to numpy for drawing
        display_image = np.array(image)
        
        # Draw gridlines
        if gridlines:
            for x in gridlines:
                scaled_x = int(x * zoom_level)
                cv2.line(display_image, 
                        (scaled_x, 0), 
                        (scaled_x, display_image.shape[0]), 
                        (255, 0, 0), 
                        line_thickness)
        
        # Draw crop points and lines
        if crop_points and len(crop_points) > 0:
            # Scale points according to zoom level
            scaled_points = [(int(x * zoom_level), int(y * zoom_level)) 
                           for x, y in crop_points]
            
            # Draw points
            for point in scaled_points:
                cv2.circle(display_image, point, 5, (0, 255, 0), -1)
            
            # Draw lines between points
            if len(scaled_points) > 1:
                for i in range(len(scaled_points)):
                    pt1 = scaled_points[i]
                    pt2 = scaled_points[(i + 1) % len(scaled_points)]
                    cv2.line(display_image, pt1, pt2, (0, 255, 0), 2)
        
        return display_image
    
    def detect_gridlines(self, sensitivity=0.95, min_gap=20):
        """Detect vertical gridlines in image"""
        if self.current_image is None:
            return []
            
        gray = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2GRAY)
        projection = np.sum(gray, axis=0)
        projection = projection / np.max(projection)
        
        window_size = int(30)
        threshold = sensitivity
        
        valleys = []
        for i in range(window_size, len(projection) - window_size):
            window = projection[i-window_size:i+window_size]
            if projection[i] < threshold and np.mean(window) < threshold:
                valleys.append(i)
                
        # Group nearby valleys with minimum gap
        grouped_valleys = []
        if valleys:
            current_group = [valleys[0]]
            for x in valleys[1:]:
                if x - current_group[-1] <= min_gap:
                    current_group.append(x)
                else:
                    if len(current_group) > window_size/4:
                        grouped_valleys.append(int(np.mean(current_group)))
                    current_group = [x]
            if len(current_group) > window_size/4:
                grouped_valleys.append(int(np.mean(current_group)))
            
        return sorted(grouped_valleys)
    
    def rotate_image(self, angle):
        """Rotate image by given angle"""
        if self.current_image is not None:
            image = Image.fromarray(self.current_image)
            rotated = image.rotate(angle, expand=True)
            self.current_image = np.array(rotated)
            self.rotation_angle = (self.rotation_angle + angle) % 360
            
    def auto_deskew(self):
        """Automatically deskew image"""
        if self.current_image is None:
            return
            
        gray = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta)
                if angle < 45:
                    angles.append(angle)
                elif angle > 135:
                    angles.append(angle - 180)
                    
            if angles:
                median_angle = np.median(angles)
                self.rotate_image(-median_angle)
    
    def crop_to_box(self, box):
        """Crop the current image to the specified box (left, top, width, height)"""
        if self.current_image is None:
            return
            
        left, top, width, height = box
        self.current_image = self.current_image[
            int(top):int(top + height),
            int(left):int(left + width)
        ]
    
    def save_image(self, gridlines=None, filename='output.png', line_thickness=1):
        """Save the current image with optional gridlines"""
        if self.current_image is None:
            return
            
        # Create a copy for saving
        save_image = self.get_display_image(gridlines=gridlines, line_thickness=line_thickness)
        
        # Save as PNG
        Image.fromarray(save_image).save(filename)

    def save_current_state(self):
        """Save the current image state"""
        if self.current_image is not None:
            self.current_image = np.array(self.current_image)
