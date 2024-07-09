import tkinter as tk
from tkinter import Menu, filedialog, messagebox, simpledialog
import random
import sqlite3
import json

class SpacedRepetition:
    def __init__(self):
        self.db_connection = sqlite3.connect('questions.db')
        self.db_cursor = self.db_connection.cursor()
        self.create_tables()

        self.root = tk.Tk()
        self.root.title("Spaced Repetition Exam Preparation")

        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        self.file_menu = Menu(self.menu)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Import Questions", command=self.import_questions)
        self.file_menu.add_command(label="View Questions", command=self.view_questions)
        self.file_menu.add_command(label="Clear Database", command=self.clear_database)

        self.topic_menu = Menu(self.menu)
        self.menu.add_cascade(label="Select Topic", menu=self.topic_menu)

        self.chapter_menu = Menu(self.menu)
        self.menu.add_cascade(label="Select Chapter", menu=self.chapter_menu)

        self.selected_chapter = tk.StringVar(self.root)
        self.selected_chapter.set("Select a Chapter")

        self.chapter_dropdown = tk.OptionMenu(self.root, self.selected_chapter, ())
        self.selected_chapter.trace("w", self.update_questions)

        self.topic_label = tk.Label(self.root, text="No Topic Selected", wraplength=300, fg="blue")
        self.topic_label.pack(pady=10)

        self.create_topic_button = tk.Button(self.root, text="Create Topic", command=self.create_topic)
        self.create_topic_button.pack(pady=5)

        self.question_label = tk.Label(self.root, text="", wraplength=300)
        self.question_label.pack(pady=10)

        self.answer_button = tk.Button(self.root, text="Show Answer", command=self.show_answer)
        self.answer_button.pack(pady=5)

        self.answer_label = tk.Label(self.root, text="", wraplength=300)
        self.answer_label.pack(pady=10)

        self.right_button = tk.Button(self.root, text="Right", command=lambda: self.mark_answer(True))
        self.wrong_button = tk.Button(self.root, text="Wrong", command=lambda: self.mark_answer(False))

        self.load_topics()
        self.root.mainloop()

    def create_tables(self):
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        """)
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY,
                topic_id INTEGER,
                name TEXT,
                UNIQUE(topic_id, name),
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            )
        """)
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY,
                chapter_id INTEGER,
                question TEXT,
                answer TEXT,
                level INTEGER,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id)
            )
        """)
        self.db_connection.commit()

    def clear_database(self):
        self.db_cursor.execute("DELETE FROM questions")
        self.db_cursor.execute("DELETE FROM chapters")
        self.db_cursor.execute("DELETE FROM topics")
        self.db_connection.commit()
        self.load_topics()
        self.topic_label.config(text="No Topic Selected")
        messagebox.showinfo("Success", "Database cleared successfully!")

    def create_topic(self):
        topic_name = simpledialog.askstring("Create Topic", "Enter topic name:")
        if topic_name:
            self.db_cursor.execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic_name,))
            self.db_connection.commit()
            self.load_topics()

    def import_questions(self):
        if not hasattr(self, 'selected_topic_id'):
            messagebox.showerror("Error", "Please create and select a topic first!")
            return

        file_path = filedialog.askopenfilename(title="Select Question File", filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, 'r') as file:
                data = json.load(file)
                chapter_name = data.get("chapter_name")
                questions = data.get("questions")

                if chapter_name and questions:
                    self.db_cursor.execute("INSERT OR IGNORE INTO chapters (name, topic_id) VALUES (?, ?)", (chapter_name, self.selected_topic_id))
                    self.db_cursor.execute("SELECT id FROM chapters WHERE name=? AND topic_id=?", (chapter_name, self.selected_topic_id))
                    chapter_id = self.db_cursor.fetchone()[0]

                    for question in questions:
                        self.db_cursor.execute("""
                            INSERT INTO questions (chapter_id, question, answer, level) 
                            VALUES (?, ?, ?, 1)
                        """, (chapter_id, question['question'], question['answer']))

                    self.db_connection.commit()
                    self.load_chapters_for_topic()
                    messagebox.showinfo("Success", "Questions imported successfully!")
                else:
                    messagebox.showerror("Error", "Invalid file format!")

    def load_topics(self):
        self.db_cursor.execute("SELECT name FROM topics")
        topics = [row[0] for row in self.db_cursor.fetchall()]
        self.topic_menu.delete(1, "end")
        for topic in topics:
            self.topic_menu.add_command(label=topic, command=lambda value=topic: self.select_topic(value))

    def select_topic(self, topic_name):
        self.db_cursor.execute("SELECT id FROM topics WHERE name=?", (topic_name,))
        self.selected_topic_id = self.db_cursor.fetchone()[0]
        self.topic_label.config(text=f"Selected Topic: {topic_name}")
        self.selected_chapter.set("Select a Chapter")
        self.load_chapters_for_topic()

    def load_chapters_for_topic(self):
        self.db_cursor.execute("SELECT name FROM chapters WHERE topic_id=?", (self.selected_topic_id,))
        chapters = [row[0] for row in self.db_cursor.fetchall()]
        self.chapter_menu.delete(0, "end")
        for chapter in chapters:
            self.chapter_menu.add_command(label=chapter, command=lambda value=chapter: self.selected_chapter.set(value))
        self.update_questions()

    def update_questions(self, *args):
        chapter_name = self.selected_chapter.get()
        if chapter_name == "Select a Chapter":
            self.questions = []
            self.inform_user("Select a chapter to view questions")
            return

        self.db_cursor.execute("SELECT id FROM chapters WHERE name=? AND topic_id=?", (chapter_name, self.selected_topic_id))
        chapter_id = self.db_cursor.fetchone()

        if chapter_id:
            chapter_id = chapter_id[0]
            self.db_cursor.execute("SELECT question, answer, level FROM questions WHERE chapter_id=?", (chapter_id,))
            self.questions = [{"question": row[0], "answer": row[1], "level": row[2]} for row in self.db_cursor.fetchall()]
            self.question_levels = {question['question']: question['level'] for question in self.questions}
            self.inform_user(f"{chapter_name} Questions Selected")
            self.next_question()
        else:
            self.questions = []
            self.inform_user(f"Chapter '{chapter_name}' not found")

    def inform_user(self, message):
        self.question_label.config(text=message)
        self.answer_label.config(text="")
        self.answer_button.pack_forget()
        self.right_button.pack_forget()
        self.wrong_button.pack_forget()

    def next_question(self):
        self.answer_label.config(text="")
        self.right_button.pack_forget()
        self.wrong_button.pack_forget()

        if not self.questions:
            self.question_label.config(text="No questions available for this chapter.")
            return

        total_levels = sum(self.question_levels.values())
        probabilities = [total_levels / self.question_levels[q['question']] for q in self.questions]
        self.current_question = random.choices(self.questions, weights=probabilities, k=1)[0]

        self.question_label.config(text=f"Question: {self.current_question['question']}")
        self.answer_button.pack(pady=5)

    def show_answer(self):
        self.answer_label.config(text=f"Answer: {self.current_question['answer']}")
        self.answer_button.pack_forget()
        self.right_button.pack(side=tk.LEFT, padx=20)
        self.wrong_button.pack(side=tk.RIGHT, padx=20)

    def mark_answer(self, correct):
        question_text = self.current_question['question']
        current_level = self.question_levels[question_text]
        new_level = min(4, current_level + 1) if correct else max(1, current_level - 1)
        self.question_levels[question_text] = new_level

        # Update the level in the database
        self.db_cursor.execute("UPDATE questions SET level = ? WHERE question = ?", (new_level, question_text))
        self.db_connection.commit()

        self.next_question()

    def view_questions(self):
        self.view_window = tk.Toplevel(self.root)
        self.view_window.title("View Questions")

        chapter_name = self.selected_chapter.get()
        if chapter_name == "Select a Chapter":
            messagebox.showerror("Error", "Please select a chapter first.")
            return

        self.db_cursor.execute("SELECT id FROM chapters WHERE name=? AND topic_id=?", (chapter_name, self.selected_topic_id))
        chapter_id = self.db_cursor.fetchone()

        if not chapter_id:
            messagebox.showerror("Error", f"Chapter '{chapter_name}' not found.")
            return

        chapter_id = chapter_id[0]
        self.db_cursor.execute("SELECT question, answer, level FROM questions WHERE chapter_id=?", (chapter_id,))
        questions = self.db_cursor.fetchall()

        # Create a canvas and a scrollbar
        canvas = tk.Canvas(self.view_window)
        scrollbar = tk.Scrollbar(self.view_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and the scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add questions to the scrollable frame
        questions_text = "\n".join([f"Q: {q[0]} (Level: {q[2]}) - A: {q[1]}" for q in questions])
        questions_label = tk.Label(scrollable_frame, text=questions_text, justify=tk.LEFT, wraplength=500)
        questions_label.pack(pady=10)

if __name__ == "__main__":
    SpacedRepetition()
