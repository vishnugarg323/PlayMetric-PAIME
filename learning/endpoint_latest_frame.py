# Add this endpoint to learning service main.py after line 1665 (after get_frame_analysis endpoint)

@app.get("/api/learning/sessions/{session_id}/frames/latest")
async def get_latest_frame(session_id: str):
    """Get the latest analyzed frame with screenshot"""
    import base64
    import os
    
    try:
        # Get session info
        session = await db_manager.fetch_one(
            "SELECT frames_analyzed, total_frames FROM learning_sessions WHERE id = $1",
            session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get latest frame with analysis
        frame = await db_manager.fetch_one(
            """SELECT frame_number, frame_path, timestamp_ms,
                      combined_summary, learning_insights, scene_type,
                      analysis_status, analyzed_at
               FROM video_frames
               WHERE learning_session_id = $1 AND analysis_status = 'completed'
               ORDER BY frame_number DESC
               LIMIT 1""",
            session_id
        )
        
        if not frame:
            # No frames analyzed yet
            return {
                "frames_analyzed": session["frames_analyzed"],
                "total_frames": session["total_frames"],
                "screenshot_base64": None,
                "analysis": None
            }
        
        # Read screenshot file and convert to base64
        screenshot_base64 = None
        if frame["frame_path"] and os.path.exists(frame["frame_path"]):
            with open(frame["frame_path"], "rb") as f:
                screenshot_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Parse combined_summary JSON for analysis data
        analysis = None
        if frame["combined_summary"]:
            try:
                import json
                summary = json.loads(frame["combined_summary"])
                analysis = {
                    "scene_type": frame["scene_type"] or summary.get("scene_type"),
                    "scene_description": summary.get("scene_description"),
                    "ocr_text": summary.get("ocr_text"),
                    "touch_detected": summary.get("touch_detected", False),
                    "touch_point": summary.get("touch_point"),
                    "ui_elements": summary.get("ui_elements", []),
                }
            except:
                pass
        
        # Count total touches
        touch_count = await db_manager.fetch_val(
            """SELECT COUNT(*) FROM video_frames 
               WHERE learning_session_id = $1 
               AND combined_summary::text LIKE '%\"touch_detected\": true%'""",
            session_id
        )
        
        return {
            "frame_number": frame["frame_number"],
            "timestamp_ms": frame["timestamp_ms"],
            "frames_analyzed": session["frames_analyzed"],
            "total_frames": session["total_frames"],
            "touches_detected": touch_count or 0,
            "screenshot_base64": screenshot_base64,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest frame: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
