import cv2
import numpy as np
import argparse
import os
import csv
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pechay Growth Monitoring and Feature Extraction Pipeline\n"
                    "Extracts Green Pixel Ratio (GPR), Projected Canopy Area (PCA), "
                    "and Canopy Dimensions for Multivariate Polynomial Regression."
    )
    parser.add_argument(
        "--image", 
        type=str, 
        default="test_img/pechay_test.jpeg",
        help="Path to the input image file."
    )
    parser.add_argument(
        "--headless", 
        action="store_true", 
        help="Run in headless mode (no GUI/windows; saves outputs directly to disk)."
    )
    parser.add_argument(
        "--save-csv", 
        type=str, 
        default="pechay_growth_log.csv",
        help="Path to the CSV file where daily metrics will be appended."
    )
    parser.add_argument(
        "--roi", 
        type=str, 
        default=None,
        help="Optional Region of Interest (ROI) bounding box: x_min,y_min,x_max,y_max (e.g., 100,50,600,450)"
    )
    parser.add_argument(
        "--min-area", 
        type=int, 
        default=150,
        help="Minimum contour area in pixels to filter out moss, algae, and transient noise."
    )
    parser.add_argument(
        "--hsv-lower", 
        type=str, 
        default="30,60,50",
        help="Lower HSV threshold for green segmentation (comma-separated H,S,V)."
    )
    parser.add_argument(
        "--hsv-upper", 
        type=str, 
        default="85,255,255",
        help="Upper HSV threshold for green segmentation (comma-separated H,S,V)."
    )
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["hsv", "exg"], 
        default="hsv",
        help="Segmentation mode: 'hsv' (HSV thresholding) or 'exg' (Excess Green index thresholding)."
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="output",
        help="Directory to save visual verification output images."
    )
    return parser.parse_args()

def process_image(args):
    # Resolve paths relative to script location if necessary
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    image_path = args.image
    if not os.path.isabs(image_path):
        image_path = os.path.join(script_dir, image_path)
        
    print(f"[PROCESS] Loading image: {image_path}")
    img = cv2.imread(image_path) # Read the image in BGR format
    if img is None:
        raise FileNotFoundError(f"Error: Unable to load image at {image_path}")

    # 1. ROI Parsing and Selection
    h, w, _ = img.shape
    if args.roi:
        try:
            x_min, y_min, x_max, y_max = map(int, args.roi.split(','))
            # Ensure boundaries are within image dimensions
            x_min, x_max = max(0, x_min), min(w, x_max)
            y_min, y_max = max(0, y_min), min(h, y_max)
            roi_img = img[y_min:y_max, x_min:x_max] # Crop the image to the specified ROI
            print(f"[ROI] Cropped to specified coordinates: [{x_min}, {y_min}] to [{x_max}, {y_max}]")
        except Exception as e:
            print(f"[ROI] [WARNING] Invalid ROI coordinates format. Using full image. Error: {e}")
            roi_img = img.copy()
            x_min, y_min, x_max, y_max = 0, 0, w, h
    else:
        # If no ROI specified, default is full image
        roi_img = img.copy()
        x_min, y_min, x_max, y_max = 0, 0, w, h

    # 2. Preprocessing: Noise reduction via Gaussian Blur
    blurred = cv2.GaussianBlur(roi_img, (5, 5), 0)

    # 3. Color Segmentation Engine
    if args.mode == "hsv":
        try:
            lower_vals = list(map(int, args.hsv_lower.split(',')))
            upper_vals = list(map(int, args.hsv_upper.split(',')))
            lower_g = np.array(lower_vals, dtype=np.uint8)
            upper_g = np.array(upper_vals, dtype=np.uint8)
        except Exception as e:
            print(f"[SEGMENT] [WARNING] Invalid HSV values provided. Using default ranges. Error: {e}")
            lower_g = np.array([30, 60, 50], dtype=np.uint8)
            upper_g = np.array([85, 255, 255], dtype=np.uint8)
            
        hsv_img = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_img, lower_g, upper_g)
        print(f"[SEGMENT] HSV segmentation using lower={lower_g.tolist()} and upper={upper_g.tolist()}")
        
    elif args.mode == "exg":
        # Excess Green Index: ExG = 2*G - R - B
        # Standardized agricultural vegetation index highly robust to natural lighting
        img_f = blurred.astype(np.float32)
        b, g, r = cv2.split(img_f)
        
        # Calculate raw ExG index
        exg = 2 * g - r - b
        
        # Threshold: ExG > 15 is typically recognized as green plant vegetation
        _, mask = cv2.threshold(exg, 15, 255, cv2.THRESH_BINARY)
        mask = mask.astype(np.uint8)
        print("[SEGMENT] Excess Green Index (ExG) segmentation applied with dynamic threshold > 15.")

    # 4. Morphological Post-Processing (Denoise)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 5. Contour Detection and Dimensional Analysis
    # Isolates leaves, filters moss/algae, and calculates geometric features
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_contours = []
    total_pca = 0  # Projected Canopy Area in pixels
    
    # Filter contours by size
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= args.min_area:
            valid_contours.append(contour)
            total_pca += area

    # Create visual annotations
    annotated_roi = roi_img.copy()
    
    # Compute the Bounding Box of the Union of all Valid contours
    if len(valid_contours) > 0:
        # Concatenate all contour coordinates to compute the bounding box of the entire plant canopy
        all_points = np.vstack(valid_contours)
        cw_x, cw_y, cw_w, cw_h = cv2.boundingRect(all_points)
        
        # Draw bounding box (Blue)
        cv2.rectangle(annotated_roi, (cw_x, cw_y), (cw_x + cw_w, cw_y + cw_h), (255, 0, 0), 2)
        # Draw contours (Green)
        cv2.drawContours(annotated_roi, valid_contours, -1, (0, 255, 0), 2)
        
        canopy_width = cw_w
        canopy_height = cw_h
    else:
        canopy_width = 0
        canopy_height = 0
        print("[ANALYZE] [WARNING] No valid green contours detected matching the size threshold.")

    # 6. Metrics Calculations
    total_roi_pixels = roi_img.shape[0] * roi_img.shape[1]
    gpr = (total_pca / total_roi_pixels) * 100 if total_roi_pixels > 0 else 0.0

    print(f"\n[RESULTS] Extraction Metrics:")
    print(f"  - Total ROI Pixels: {total_roi_pixels}")
    print(f"  - Projected Canopy Area (PCA): {total_pca:.1f} pixels")
    print(f"  - Green Pixel Ratio (GPR): {gpr:.3f}%")
    print(f"  - Canopy Bounding Dimensions: {canopy_width}x{canopy_height} pixels (WxH)")

    # 7. Write results to CSV (Growth Log)
    if args.save_csv:
        csv_path = args.save_csv
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(script_dir, csv_path)
            
        file_exists = os.path.isfile(csv_path)
        
        try:
            with open(csv_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists or os.stat(csv_path).st_size == 0:
                    # Write CSV Headers
                    writer.writerow([
                        "Timestamp", "Image_File", "Mode", "ROI_Coords",
                        "Total_ROI_Pixels", "Canopy_Area_Pixels", "GPR_Percent",
                        "Canopy_Width_Pixels", "Canopy_Height_Pixels"
                    ])
                
                # Append daily data row
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                image_name = os.path.basename(args.image)
                roi_str = args.roi if args.roi else "FULL"
                writer.writerow([
                    timestamp, image_name, args.mode, roi_str,
                    total_roi_pixels, round(total_pca, 1), round(gpr, 4),
                    canopy_width, canopy_height
                ])
            print(f"[LOG] Metrics successfully appended to: {csv_path}")
        except Exception as e:
            print(f"[LOG] [ERROR] Failed to write to CSV log: {e}")

    # 8. GUI or Headless Output Saving
    # Overlay metrics text onto annotated image
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(annotated_roi, f"GPR: {gpr:.2f}%", (10, 30), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated_roi, f"PCA: {int(total_pca)} px", (10, 60), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated_roi, f"Size: {canopy_width}x{canopy_height}", (10, 90), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    # Save visual verification images to output folder
    out_dir = args.output_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(script_dir, out_dir)
    os.makedirs(out_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(args.image))[0]
    out_annotated_path = os.path.join(out_dir, f"{base_name}_processed.png")
    out_mask_path = os.path.join(out_dir, f"{base_name}_mask.png")

    try:
        cv2.imwrite(out_annotated_path, annotated_roi)
        cv2.imwrite(out_mask_path, mask)
        print(f"[OUTPUT] Processed image saved to: {out_annotated_path}")
        print(f"[OUTPUT] Denoised binary mask saved to: {out_mask_path}")
    except Exception as e:
        print(f"[OUTPUT] [ERROR] Failed to save output images: {e}")

    # Show images in GUI only if NOT headless
    if not args.headless:
        print("\n[GUI] Rendering active windows. Press any key to exit.")
        cv2.imshow("Original (Cropped)", roi_img)
        cv2.imshow("Green Mask (Morphology Cleaned)", mask)
        cv2.imshow("Annotated Detections", annotated_roi)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    args = parse_args()
    process_image(args)
