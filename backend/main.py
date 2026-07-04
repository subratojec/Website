import os
import uuid
import shutil
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
import jwt
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import SessionLocal, ContentBlock, JournalEntry, Thought, Postcard

load_dotenv()

app = FastAPI()

# Allow frontend to communicate with this backend API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "secret")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    expire = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode({"sub": "admin", "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
class ContactForm(BaseModel):
    name: str
    email: str
    letter: str

@app.post("/api/contact")
async def handle_contact_form(form: ContactForm):
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    receiver_email = os.getenv("RECEIVER_EMAIL", email_user)

    if not email_user or not email_pass:
        raise HTTPException(status_code=500, detail="Email credentials are not configured on the server.")

    # Create the email content
    msg = EmailMessage()
    msg.set_content(f"Name: {form.name}\nEmail: {form.email}\n\nMessage:\n{form.letter}")
    msg['Subject'] = f"New Contact Form Submission from {form.name}"
    msg['From'] = email_user
    msg['To'] = receiver_email

    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", 587))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        return {"message": "Email sent successfully!"}
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email. Please try again later.")

class ContentBlockUpdate(BaseModel):
    content: str

@app.get("/api/content/{block_id}")
def get_content(block_id: str, db: Session = Depends(get_db)):
    block = db.query(ContentBlock).filter(ContentBlock.id == block_id).first()
    if not block:
        return {"content": ""}
    return {"content": block.content}

@app.put("/api/content/{block_id}")
def update_content(block_id: str, data: ContentBlockUpdate, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    block = db.query(ContentBlock).filter(ContentBlock.id == block_id).first()
    if block:
        block.content = data.content
    else:
        block = ContentBlock(id=block_id, content=data.content)
        db.add(block)
    db.commit()
    return {"message": "Updated"}

class JournalEntryCreate(BaseModel):
    title: str
    date: str
    content: str

class JournalEntryResponse(JournalEntryCreate):
    id: int
    
    class Config:
        from_attributes = True

@app.get("/api/blogs", response_model=List[JournalEntryResponse])
def get_journal_entries(db: Session = Depends(get_db)):
    return db.query(JournalEntry).order_by(JournalEntry.id.desc()).all()

@app.post("/api/blogs")
def create_journal_entry(data: JournalEntryCreate, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    entry = JournalEntry(title=data.title, date=data.date, content=data.content)
    db.add(entry)
    db.commit()
    return {"message": "Created"}

@app.delete("/api/blogs/{entry_id}")
def delete_journal_entry(entry_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
    return {"message": "Deleted"}

class ThoughtCreate(BaseModel):
    content: str

class ThoughtResponse(ThoughtCreate):
    id: int
    class Config: from_attributes = True

@app.get("/api/thoughts", response_model=List[ThoughtResponse])
def get_thoughts(db: Session = Depends(get_db)):
    return db.query(Thought).order_by(Thought.id.desc()).all()

@app.post("/api/thoughts")
def create_thought(data: ThoughtCreate, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    thought = Thought(content=data.content)
    db.add(thought)
    db.commit()
    return {"message": "Created"}

@app.delete("/api/thoughts/{thought_id}")
def delete_thought(thought_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    thought = db.query(Thought).filter(Thought.id == thought_id).first()
    if thought:
        db.delete(thought)
        db.commit()
    return {"message": "Deleted"}

class PostcardCreate(BaseModel):
    image_url: str

class PostcardResponse(PostcardCreate):
    id: int
    class Config: from_attributes = True

@app.get("/api/postcards", response_model=List[PostcardResponse])
def get_postcards(db: Session = Depends(get_db)):
    return db.query(Postcard).order_by(Postcard.id.desc()).all()

@app.post("/api/postcards")
def create_postcard(data: PostcardCreate, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    pc = Postcard(image_url=data.image_url)
    db.add(pc)
    db.commit()
    return {"message": "Created"}

@app.delete("/api/postcards/{postcard_id}")
def delete_postcard(postcard_id: int, db: Session = Depends(get_db), token: str = Depends(verify_token)):
    db_postcard = db.query(Postcard).filter(Postcard.id == postcard_id).first()
    if db_postcard:
        if db_postcard.image_url and "/uploads/" in db_postcard.image_url:
            old_filename = db_postcard.image_url.split('/')[-1]
            old_filepath = os.path.join("uploads", old_filename)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except Exception:
                    pass
        db.delete(db_postcard)
        db.commit()
    return {"message": "Deleted"}

import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

@app.post("/api/upload")
def upload_file(file: UploadFile = File(...), previous_url: Optional[str] = Form(None), token: str = Depends(verify_token)):
    if previous_url and "/uploads/" in previous_url:
        old_filename = previous_url.split('/')[-1]
        old_filepath = os.path.join("uploads", old_filename)
        if os.path.exists(old_filepath):
            try:
                os.remove(old_filepath)
            except Exception:
                pass

    if os.getenv("CLOUDINARY_CLOUD_NAME"):
        try:
            result = cloudinary.uploader.upload(file.file)
            return {"url": result.get("secure_url")}
        except Exception as e:
            print(f"Cloudinary upload failed: {e}")
            raise HTTPException(status_code=500, detail="Cloudinary upload failed")

    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = f"uploads/{filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"http://localhost:8000/uploads/{filename}"}

@app.get("/admin")
def serve_admin():
    import os
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    raise HTTPException(status_code=404, detail="Admin panel not found")


