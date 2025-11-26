from planner_agent import PlannerAgent
from data_agent import DataAgent
from communicator_agent import CommunicatorAgent
from gemini_agent import GeminiAgent
from root_agent import RootAgent

def main():
    planner = PlannerAgent()
    data_agent = DataAgent()
    communicator = CommunicatorAgent()
    gemini = GeminiAgent()

    root = RootAgent(planner, data_agent, communicator, gemini)

    print("Hey! Your Trail Buddy is ready! 🌲")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit","quit"]:
            print("Goodbye! Enjoy your hike! 🌄")
            break
        response = root.handle_message(user_input)
        print("Agent:", response)

if __name__ == "__main__":
    main()
