import cv2
from app.perception.yolo_detector import YOLODetector
from app.tracking.bytetrack_wrapper import ByteTrackTracker

from app.domain.frame import Frame

def run():
    # Initialize AI
    detector = YOLODetector()
    tracker = ByteTrackTracker(camera_id='test')

    cap = cv2.VideoCapture(r'C:\Users\Harshal\Downloads\videoplayback.mp4')
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    tracks_history = {}

    for frame_idx in range(400):
        ret, frame_img = cap.read()
        if not ret: break
        
        frame = Frame(frame_id=str(frame_idx), camera_id='test', data=frame_img, timestamp=0.0)
        detections = detector.detect(frame)
        tracks = tracker.update(detections, frame)
        
        for t in tracks:
            tid = t.track_id
            # Calculate center bottom (typical reference point)
            cx = (t.bounding_box.left + t.bounding_box.right) / 2 / width
            cy = t.bounding_box.bottom / height
            
            if tid not in tracks_history:
                tracks_history[tid] = []
            tracks_history[tid].append({'f': frame_idx, 'x': cx, 'y': cy})

    cap.release()

    # Find the longest track
    if not tracks_history:
        print("No tracks found.")
        return
        
    longest_tid = max(tracks_history.keys(), key=lambda k: len(tracks_history[k]))
    path = tracks_history[longest_tid]
    print(f'Track ID: {longest_tid}, Length: {len(path)}')
    print(f'Start: {path[0]}')
    print(f'Mid: {path[len(path)//2]}')
    print(f'End: {path[-1]}')

if __name__ == '__main__':
    run()
