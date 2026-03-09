# AWS Cost Monitoring & Cleanup Automation

## 📌 Overview
This project automates **AWS cost monitoring** and **resource cleanup** with a safety-first approach.  
It ensures that unused resources are only terminated when spend exceeds a configurable threshold, helping prevent unexpected billing spikes.

## ⚙️ Components
The framework consists of three scripts:

1. **check_cost.py**  
   - Fetches daily AWS spend using the Cost Explorer API.  
   - Prints detailed reports with daily usage and weekly summaries.  

2. **aws_cleanup.py**  
   - Cleans up unused AWS resources globally (EC2, RDS, VPCs, ELBs, EKS, EIPs, EBS).  
   - Generates logs (`aws_cleanup.log`) for transparency.  

3. **controller.py**  
   - Orchestrates the workflow.  
   - Runs the cost check, prints reports, and compares spend against a threshold.  
   - Triggers cleanup only when the threshold is exceeded.  
   - Optional confirmation prompt for safety.

## 📂 Project Structure

aws-cost-monitoring/ 
│ ├── scripts/ │   
    ├── check_cost.py          # AWS Cost Explorer script │   
    ├── aws_cleanup.py         # Global cleanup script │   
    └── controller.py          # Orchestrator script │ 
├── logs/ 
    │   └── aws_cleanup.log        # Cleanup log file │ 
├── config/ │   
└── settings.json          # Thresholds, regions, 
exclusions │ 
├── README.md                
 Documentation 
└── requirements.txt           # Python dependencies


## 🔧 Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/<your-username>/aws-cost-monitoring.git
   cd aws-cost-monitoring


- Install dependencies:

pip install -r requirements.txt


- Configure AWS CLI with appropriate credentials

aws configure

- Update config/settings.json with your threshold and region preferences:


{
  "threshold": 10.0,
  "regions": ["us-east-1", "us-west-2"],
  "exclude_default_vpc": true
}


Run the controller script:

python scripts/controller.py
