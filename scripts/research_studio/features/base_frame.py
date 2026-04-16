"""A base class that gives all features access to the main app's loading indicators."""

import customtkinter as ctk

class BaseFeatureFrame(ctk.CTkFrame):
    
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.app = app_instance