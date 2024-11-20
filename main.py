from flask import Flask, request, jsonify
from pdfminer.high_level import extract_text
from openai import OpenAI
import os
import tempfile
from flask_cors import CORS
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Create an OpenAI client using the API key
client = OpenAI(api_key=api_key)



app = Flask(__name__)
CORS(app)

experience_headings = [
    'experience', 'work experience', 'professional experience',
    'employment history', 'work history'
]

other_headings = [
    'education', 'skills', 'projects', 'certifications',
    'publications', 'awards', 'interests', 'languages',
    'references', 'contact', 'summary', 'objective',
    'personal details', 'profile', 'additional information'
]

def extract_pdf_text(pdf_path):
    return extract_text(pdf_path)

def extract_experience_section(text):
    # Normalize text to lower case
    text_lower = text.lower()
    
    # Split text into lines
    lines = text_lower.split('\n')
    
    experience_text = ''
    in_experience_section = False

    for line in lines:
        stripped_line = line.strip()
        
        # Check if the line is an experience heading
        if any(stripped_line == heading for heading in experience_headings):
            in_experience_section = True
            continue
        
        # Check if the line is another section heading
        if any(stripped_line == heading for heading in other_headings):
            if in_experience_section:
                break  # End of Experience section
            else:
                continue
        
        if in_experience_section:
            experience_text += line + '\n'
    
    return experience_text.strip()

def create_prompt(experience_text, job_description):
    user_prompt = (
        "Please help me rephrase and enhance my work experience descriptions to better match the following job description. "
        "Emphasize relevant skills, technologies, and responsibilities that align with the job requirements, while ensuring all information remains truthful"
        "Do not add any new information or make up experiences I did not have. Do not bold any words and do not make it extremely formal:\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Experience:\n{experience_text}"
    )
    return user_prompt

def get_chatgpt_response(prompt):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4o-mini",
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@app.route('/process_resumee', methods=['POST'])
def process_resume():
    
    job_desc = request.form.get('job_desc')
    resume_file = request.files.get('resume')
    

   
    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        
        resume_file.save(temp_file.name)
        temp_path = temp_file.name
    

    try:
        # Extract experience section from the resume
        text = extract_pdf_text(temp_path)
        experience_section = extract_experience_section(text)
        

        if not experience_section:
            return jsonify({'error': 'Experience section not found in resume'}), 400

        # Create the prompt for ChatGPT
        prompt = create_prompt(experience_section, job_desc)
        

        # Get the response from ChatGPT
        response = get_chatgpt_response(prompt)
        

        if response:
            
            return jsonify({'modified_experience': response}), 200
        else:
            return jsonify({'error': 'Failed to get a response from ChatGPT'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
