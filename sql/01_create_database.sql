/* DGCP Public Procurement Analytics - Step 1: Create database */
IF DB_ID(N'DGCP_Procurement') IS NULL
BEGIN
    CREATE DATABASE DGCP_Procurement;
END;
GO
USE DGCP_Procurement;
GO
