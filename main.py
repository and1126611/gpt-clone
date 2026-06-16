import asyncio
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool


if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="Life Coach Agent",
        instructions="""
        You are an outstanding life coach, 
        particularly skilled at motivating the user and empowering user to reach their full potential.  
        You have access to the followign tools:
            - Web Search Tool: Use this when the user asks a questions that isn't in your training data.
              Use this to learn about current events. 
              When you think you don't know the answer, try searching for it on the web first.
              You are an expert on searching high quality contents on the web
              related to Motivation, self-development tips, habit formation advices.
        """, 
        tools=[
            WebSearchTool(
             #user_location="South Korea",
              search_context_size="medium",
            ),
        ],
    )
agent = st.session_state["agent"]

if "session" not in st.session_state:
	st.session_state["session"] = SQLiteSession(
			"chat-history",
			"life-coach-agent-memory.db"
	)

session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"])
    
        if "type" in message and message["type"] == "web_search_call":
            with st.chat_message("ai"):
                st.write("Searched the web...")

def update_status(status_container, event):
    #mapper
    status_messages = {
        #set the name of event as a mapper key : and then map info of label, state
        "response.web_search_call.completed": (
            "Web search completed.", 
            "complete"
        ),
        "response.web_search_call.in_progress": (
            "Starting web search...",
            "running",
        ),
        "response.web_search_call.searching": (
            "Web search in progress...",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)

asyncio.run(paint_history())


async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        response = ""
        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

    async for event in stream.stream_events():
        if event.type == "raw_response_event":

            # event.data.type == "response.web_search_call.???"에 따라: print status 
            # 대신 >> update_status function으로 따로 뺀다. (elif 대신 딕션어리로 처리 가능)
            update_status(status_container, event.data.type)
            if event.data.type == "response.web_search_call.searching":
                print("Coach: 웹 검색 중..")
                continue

            if event.data.type == "response.output_text.delta":
                response += event.data.delta
                text_placeholder.write(response)
    print("Coach:",response)

prompt = st.chat_input("Write a message for your assistant")
if prompt:
    with st.chat_message("human"):
        st.write(prompt)
        print("User:",prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    reset = st.button("Reset Memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))