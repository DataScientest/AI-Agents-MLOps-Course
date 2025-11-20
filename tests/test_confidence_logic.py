import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/app')

import psycopg
from psycopg.rows import dict_row
from confidence import get_recommendation, CONFIDENCE_THRESHOLDS

def main():
    # Database connection
    postgres_uri = "postgresql://agent_user:agent_password@postgres:5432/agent_checkpoints"
    
    try:
        with psycopg.connect(postgres_uri) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Fetch stats for our test service
                cur.execute("""
                    SELECT service_name, alert_type, total_diagnoses, successful_diagnoses, confidence_score 
                    FROM alert_type_stats 
                    WHERE total_diagnoses > 0
                    ORDER BY confidence_score DESC
                """)
                
                rows = cur.fetchall()
                
                print("\n🔍 Confidence Decision Logic Test")
                print("=================================")
                print(f"Thresholds: Auto > {CONFIDENCE_THRESHOLDS['auto_remediate']:.0%}, Suggest > {CONFIDENCE_THRESHOLDS['suggest']:.0%}\n")
                
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
