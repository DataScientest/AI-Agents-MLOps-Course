import os
import psycopg
from psycopg.rows import dict_row

# Configuration - Try changing these!
THRESHOLDS = {
    "auto_remediate": 0.9,  # 90% confidence required for auto-fix
    "suggest": 0.7,         # 70% confidence required for suggestion
    "escalate": 0.0         # Fallback
}

def get_recommendation(confidence_score, total_diagnoses):
    """
    Determines the recommended action based on confidence score.
    """
    if total_diagnoses < 3:
        return "escalate", "Not enough data (need 3+ diagnoses)"
        
    if confidence_score >= THRESHOLDS["auto_remediate"]:
        return "auto_remediate", f"High confidence ({confidence_score:.1%}) - Safe to automate"
    
    if confidence_score >= THRESHOLDS["suggest"]:
        return "suggest", f"Medium confidence ({confidence_score:.1%}) - Human review needed"
        
    return "escalate", f"Low confidence ({confidence_score:.1%}) - Escalate to human"

def main():
    # Database connection
    postgres_uri = "postgresql://agent_user:agent_password@postgres:5432/agent_checkpoints"
    
    try:
        with psycopg.connect(postgres_uri) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Fetch stats for our test service
                cur.execute("""
                    SELECT service_name, alert_type, total_diagnoses, confidence_score 
                    FROM alert_type_stats 
                    WHERE total_diagnoses > 0
                    ORDER BY confidence_score DESC
                """)
                
                rows = cur.fetchall()
                
                print("\n🔍 Confidence Decision Logic Test")
                print("=================================")
                print(f"Thresholds: Auto > {THRESHOLDS['auto_remediate']:.0%}, Suggest > {THRESHOLDS['suggest']:.0%}\n")
                
                if not rows:
                    print("No stats found. Run the previous exercise to generate data!")
                    return

                for row in rows:
                    action, reason = get_recommendation(
                        row["confidence_score"], 
                        row["total_diagnoses"]
                    )
                    
                    print(f"Service:    {row['service_name']}")
                    print(f"Alert:      {row['alert_type']}")
                    print(f"Stats:      {row['successful_diagnoses']}/{row['total_diagnoses']} successes ({row['confidence_score']:.1%})")
                    print(f"Action:     👉 {action.upper()}")
                    print(f"Reason:     {reason}")
                    print("-" * 50)

    except Exception as e:
        print(f"Error: {e}")
        print("\nTip: Run this script inside the container:")
        print("docker exec -it ai-agents-mlops-course-aiops-agent-monitor-1 python /app/tests/test_confidence_logic.py")

if __name__ == "__main__":
    main()
