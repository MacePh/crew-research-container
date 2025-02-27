import os
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import WebsiteSearchTool, GithubSearchTool, SerperDevTool

# Load environment variables
load_dotenv()

# Verify API key is loaded
serper_api_key = os.getenv("SERPER_API_KEY")
if not serper_api_key:
    raise ValueError("SERPER_API_KEY not found in environment variables")

tool=SerperDevTool()
@CrewBase
class ResearchCrewCrew:
    """ResearchCrewCrew crew"""

    def __init__(self):
        self.inputs = {}
        self.tasks_config = self.load_tasks_config()
        self.agents_config = self.load_agents_config()

    def load_tasks_config(self):
        """Load tasks configuration from YAML file"""
        import yaml
        
        # Get the base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "src", "research_crew_crew", "config", "tasks.yaml")
        
        # Fall back to relative path if absolute path doesn't exist
        if not os.path.exists(config_path):
            # Try alternate paths
            alternate_paths = [
                "/app/research_crew_crew/src/research_crew_crew/config/tasks.yaml",
                "research_crew_crew/src/research_crew_crew/config/tasks.yaml",
                "src/research_crew_crew/config/tasks.yaml",
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "tasks.yaml"),
                os.path.join(base_dir, "research_crew_crew", "src", "research_crew_crew", "config", "tasks.yaml"),
                os.path.join("research_crew_crew", "config", "tasks.yaml"),
                os.path.join("config", "tasks.yaml"),
            ]
            
            for path in alternate_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        print(f"Loading tasks config from: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def load_agents_config(self):
        """Load agents configuration from YAML file"""
        import yaml
        
        # Get the base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "src", "research_crew_crew", "config", "agents.yaml")
        
        # Fall back to relative path if absolute path doesn't exist
        if not os.path.exists(config_path):
            # Try alternate paths
            alternate_paths = [
                "/app/research_crew_crew/src/research_crew_crew/config/agents.yaml",
                "research_crew_crew/src/research_crew_crew/config/agents.yaml",
                "src/research_crew_crew/config/agents.yaml",
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "agents.yaml"),
                os.path.join(base_dir, "research_crew_crew", "src", "research_crew_crew", "config", "agents.yaml"),
                os.path.join("research_crew_crew", "config", "agents.yaml"),
                os.path.join("config", "agents.yaml"),
            ]
            
            for path in alternate_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        print(f"Loading agents config from: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    @agent
    def research_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["research_specialist"],
            tools=[SerperDevTool(serper_api_key=serper_api_key)],
        )

    @agent
    def github_explorer(self) -> Agent:
        return Agent(
            config=self.agents_config["github_explorer"],
            tools=[
                GithubSearchTool(
                    gh_token=os.getenv("GITHUB_TOKEN"),
                    content_types=["code", "repositories"],
                )
            ],
        )

    @agent
    def flow_designer(self) -> Agent:
        return Agent(
            config=self.agents_config["flow_designer"],
            tools=[],
        )

    @agent
    def implementation_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["implementation_planner"],
            tools=[WebsiteSearchTool()],
        )

    @agent
    def prompt_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["prompt_generator"],
            tools=[WebsiteSearchTool()],
        )

    @task
    def research_topic_task(self) -> Task:
        config = self.tasks_config["research_topic_task"]
        return Task(
            description=config["description"].format(**self.inputs)
            if self.inputs
            else config["description"],
            expected_output=config["expected_output"].format(**self.inputs)
            if self.inputs
            else config["expected_output"],
            tools=[SerperDevTool(serper_api_key=serper_api_key)],
            agent=self.research_specialist(),
        )

    @task
    def search_github_task(self) -> Task:
        config = self.tasks_config["search_github_task"]
        return Task(
            description=config["description"].format(**self.inputs)
            if self.inputs
            else config["description"],
            expected_output=config["expected_output"].format(**self.inputs)
            if self.inputs
            else config["expected_output"],
            tools=[
                GithubSearchTool(
                    gh_token=os.getenv("GITHUB_TOKEN"),
                    content_types=["code", "repositories"],
                )
            ],
            agent=self.github_explorer(),
        )

    @task
    def design_flow_task(self) -> Task:
        config = self.tasks_config["design_flow_task"]
        
        # Simple description without all the extra instructions
        description = config["description"]
        if self.inputs:
            description = description.format(**self.inputs)
        
        return Task(
            description=description,
            expected_output=config["expected_output"].format(**self.inputs)
            if self.inputs
            else config["expected_output"],
            tools=[],
            agent=self.flow_designer(),
        )

    @task
    def create_game_plan_task(self) -> Task:
        config = self.tasks_config["create_game_plan_task"]
        return Task(
            description=config["description"].format(**self.inputs)
            if self.inputs
            else config["description"],
            expected_output=config["expected_output"].format(**self.inputs)
            if self.inputs
            else config["expected_output"],
            tools=[],
            agent=self.implementation_planner(),
        )

    @task
    def generate_prompt_task(self) -> Task:
        config = self.tasks_config["generate_prompt_task"]
        return Task(
            description=config["description"].format(**self.inputs)
            if self.inputs
            else config["description"],
            expected_output=config["expected_output"].format(**self.inputs)
            if self.inputs
            else config["expected_output"],
            tools=[],
            agent=self.prompt_generator(),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ResearchCrewCrew crew"""
        # Get inputs
        user_goal = self.inputs.get("user_goal", "")
        crew_name = self.inputs.get("crew_name", "research_crew")
        
        # Define report directory and ensure it exists
        # Check for Docker environment first, then try relative paths
        reports_dirs = [
            "/app/reports",                # Docker container path
            "reports",                     # Relative to current directory
            os.path.abspath("reports"),    # Absolute path relative to current directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports")  # From module path
        ]
        
        reports_dir = None
        for path in reports_dirs:
            # Create directory if it doesn't exist
            os.makedirs(path, exist_ok=True)
            # Check if we can write to it
            try:
                test_file = os.path.join(path, ".test_write")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)  # Clean up
                reports_dir = path
                print(f"Using reports directory: {reports_dir}")
                break
            except (IOError, PermissionError):
                continue
        
        if not reports_dir:
            # If all attempts fail, use the current directory
            reports_dir = os.getcwd()
            print(f"WARNING: Could not find or create reports directory. Using current directory: {reports_dir}")
        
        # Create tasks
        research_task = self.research_topic_task()
        github_task = self.search_github_task()
        flow_task = self.design_flow_task()
        create_game_plan_task = self.create_game_plan_task()
        prompt_task = self.generate_prompt_task()
        
        # Initialize crew
        crew = Crew(
            agents=[
                self.research_specialist(),
                self.github_explorer(),
                self.flow_designer(),
                self.implementation_planner(),
                self.prompt_generator()
            ],
            tasks=[
                research_task,
                github_task,
                flow_task,
                create_game_plan_task,
                prompt_task
            ],
            process=Process.sequential,
            verbose=True,
        )
        
        # Run the crew
        result = crew.kickoff(inputs=self.inputs)
        
        # Write to report.md
        if self.inputs and "user_goal" in self.inputs:
            try:
                report_path = os.path.join(reports_dir, f"{crew_name}_report.md")
                
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"# Topic: {self.inputs['user_goal']}\n\n")
                    f.write(f"## Crew Name: {crew_name}\n\n")
                    
                    task_configs = [
                        self.tasks_config["research_topic_task"],
                        self.tasks_config["search_github_task"],
                        self.tasks_config["design_flow_task"],
                        self.tasks_config["create_game_plan_task"],
                        self.tasks_config["generate_prompt_task"],
                    ]
                    
                    for i, task in enumerate(crew.tasks):
                        desc = (
                            task_configs[i]["description"].format(**self.inputs)
                            if self.inputs
                            else task_configs[i]["description"]
                        )
                        
                        # Get agent name
                        agent_name = task.agent.__class__.__name__
                        
                        # Ensure we have output
                        actual_output = "No output generated"
                        if hasattr(task, "output") and task.output:
                            # Convert TaskOutput to string if needed
                            if hasattr(task.output, "__str__"):
                                actual_output = str(task.output)
                            else:
                                # If it's already a string or has no __str__ method
                                try:
                                    actual_output = str(task.output)
                                except:
                                    actual_output = "Error: Could not convert output to string"
                        
                        # Write to file
                        f.write(f"## {desc} (Agent: {agent_name})\n\n")
                        f.write(f"**Output:**\n\n{actual_output}\n\n")
                
                print(f"Successfully wrote to {report_path}")
                
            except Exception as e:
                print(f"Error writing to report file: {e}")
        
        return crew

    def run_crew(self, crew_name="default_crew"):
        """Run the crew with the current configuration"""
        result = self.crew().kickoff()
        
        # Save the report to a file
        # Check for Docker environment first, then try relative paths
        reports_dirs = [
            "/app/reports",                # Docker container path
            "reports",                     # Relative to current directory
            os.path.abspath("reports"),    # Absolute path relative to current directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports")  # From module path
        ]
        
        reports_dir = None
        for path in reports_dirs:
            # Create directory if it doesn't exist
            os.makedirs(path, exist_ok=True)
            # Check if we can write to it
            try:
                test_file = os.path.join(path, ".test_write")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)  # Clean up
                reports_dir = path
                print(f"Using reports directory: {reports_dir}")
                break
            except (IOError, PermissionError):
                continue
        
        if not reports_dir:
            # If all attempts fail, use the current directory
            reports_dir = os.getcwd()
            print(f"WARNING: Could not find or create reports directory. Using current directory: {reports_dir}")
        
        report_path = os.path.join(reports_dir, f"{crew_name}_report.md")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Topic: {self.inputs['user_goal']}\n\n")
            f.write(f"## Crew Name: {crew_name}\n\n")
            
            task_configs = [
                self.tasks_config["research_topic_task"],
                self.tasks_config["search_github_task"],
                self.tasks_config["design_flow_task"],
                self.tasks_config["create_game_plan_task"],
                self.tasks_config["generate_prompt_task"],
            ]
            
            for i, task in enumerate(result.crew.tasks):
                desc = (
                    task_configs[i]["description"].format(**self.inputs)
                    if self.inputs
                    else task_configs[i]["description"]
                )
                
                # Get agent name
                agent_name = task.agent.__class__.__name__
                
                # Ensure we have output
                actual_output = "No output generated"
                if hasattr(task, "output") and task.output:
                    # Convert TaskOutput to string if needed
                    if hasattr(task.output, "__str__"):
                        actual_output = str(task.output)
                    else:
                        # If it's already a string or has no __str__ method
                        try:
                            actual_output = str(task.output)
                        except:
                            actual_output = "Error: Could not convert output to string"
                
                # Write to file
                f.write(f"## {desc} (Agent: {agent_name})\n\n")
                f.write(f"**Output:**\n\n{actual_output}\n\n")
