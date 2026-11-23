--
-- PostgreSQL database dump
--

\restrict S6s6L4838yUzJf6nHAufHCyDigDkpUwJyN4qCHkxYZaERcvYeWCeH8wZo97lThs

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: infrascan_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO infrascan_user;

--
-- Name: infrastructure_assets; Type: TABLE; Schema: public; Owner: infrascan_user
--

CREATE TABLE public.infrastructure_assets (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(8) NOT NULL,
    location character varying(500) NOT NULL,
    status character varying(17) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.infrastructure_assets OWNER TO infrascan_user;

--
-- Name: infrastructure_assets_id_seq; Type: SEQUENCE; Schema: public; Owner: infrascan_user
--

CREATE SEQUENCE public.infrastructure_assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.infrastructure_assets_id_seq OWNER TO infrascan_user;

--
-- Name: infrastructure_assets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: infrascan_user
--

ALTER SEQUENCE public.infrastructure_assets_id_seq OWNED BY public.infrastructure_assets.id;


--
-- Name: inspections; Type: TABLE; Schema: public; Owner: infrascan_user
--

CREATE TABLE public.inspections (
    id integer NOT NULL,
    asset_id integer NOT NULL,
    inspector_id integer,
    inspection_date timestamp with time zone DEFAULT now() NOT NULL,
    findings text,
    status character varying(11) NOT NULL
);


ALTER TABLE public.inspections OWNER TO infrascan_user;

--
-- Name: inspections_id_seq; Type: SEQUENCE; Schema: public; Owner: infrascan_user
--

CREATE SEQUENCE public.inspections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inspections_id_seq OWNER TO infrascan_user;

--
-- Name: inspections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: infrascan_user
--

ALTER SEQUENCE public.inspections_id_seq OWNED BY public.inspections.id;


--
-- Name: predictions; Type: TABLE; Schema: public; Owner: infrascan_user
--

CREATE TABLE public.predictions (
    id integer NOT NULL,
    asset_id integer NOT NULL,
    predicted_failure_date timestamp with time zone,
    confidence_score double precision NOT NULL,
    recommended_action text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    image_path character varying(500),
    image_filename character varying(255),
    severity_level character varying(100) DEFAULT 'Moderate Damage'::character varying,
    defect_summary text,
    defect_details jsonb
);


ALTER TABLE public.predictions OWNER TO infrascan_user;

--
-- Name: predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: infrascan_user
--

CREATE SEQUENCE public.predictions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.predictions_id_seq OWNER TO infrascan_user;

--
-- Name: predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: infrascan_user
--

ALTER SEQUENCE public.predictions_id_seq OWNED BY public.predictions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: infrascan_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO infrascan_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: infrascan_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO infrascan_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: infrascan_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: infrastructure_assets id; Type: DEFAULT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.infrastructure_assets ALTER COLUMN id SET DEFAULT nextval('public.infrastructure_assets_id_seq'::regclass);


--
-- Name: inspections id; Type: DEFAULT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.inspections ALTER COLUMN id SET DEFAULT nextval('public.inspections_id_seq'::regclass);


--
-- Name: predictions id; Type: DEFAULT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.predictions ALTER COLUMN id SET DEFAULT nextval('public.predictions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: infrascan_user
--

COPY public.alembic_version (version_num) FROM stdin;
7c99d0db12db
\.


--
-- Data for Name: infrastructure_assets; Type: TABLE DATA; Schema: public; Owner: infrascan_user
--

COPY public.infrastructure_assets (id, name, type, location, status, created_at) FROM stdin;
2	Water Treatment Plant A	BUILDING	North Industrial Park	OPERATIONAL	2026-10-31 13:24:03.337055+05:30
1	Main Highway Bridge	BRIDGE	Sector 5, Chennai	OPERATIONAL	2026-11-04 14:53:29.458505+05:30
\.


--
-- Data for Name: inspections; Type: TABLE DATA; Schema: public; Owner: infrascan_user
--

COPY public.inspections (id, asset_id, inspector_id, inspection_date, findings, status) FROM stdin;
2	2	4	2026-10-31 17:30:00+05:30	Minor rust observed on the primary support beam.	PENDING
\.


--
-- Data for Name: predictions; Type: TABLE DATA; Schema: public; Owner: infrascan_user
--

COPY public.predictions (id, asset_id, predicted_failure_date, confidence_score, recommended_action, created_at, image_path, image_filename, severity_level, defect_summary, defect_details) FROM stdin;
2	2	2027-05-15 00:00:00+05:30	0.92	Replace secondary support cables.	2026-10-31 13:35:47.230435+05:30	\N	\N	Moderate Damage	\N	\N
3	1	2027-02-02 15:19:10.747818+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-04 15:19:10.757608+05:30	uploads/de1147efef5246ad941c3e46e63835f7_20261104_151910.jpeg	de1147efef5246ad941c3e46e63835f7_20261104_151910.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
4	1	2027-02-02 15:19:20.216914+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-04 15:19:20.219537+05:30	uploads/52bbc68ebcb44001bf1747fb022465e5_20261104_151920.jpeg	52bbc68ebcb44001bf1747fb022465e5_20261104_151920.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
5	1	2027-02-02 15:19:51.107263+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-04 15:19:51.1097+05:30	uploads/70b395eab4964292850ed546d2cd9c49_20261104_151951.jpeg	70b395eab4964292850ed546d2cd9c49_20261104_151951.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
6	1	2027-02-02 19:47:11.857002+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-04 19:47:11.859431+05:30	uploads/313557ac63e7427fb2c3afe50b84cd1b_20261104_194711.jpeg	313557ac63e7427fb2c3afe50b84cd1b_20261104_194711.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
7	2	2027-02-08 20:58:19.808324+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-10 20:58:19.810805+05:30	uploads/5f8c473f81a749f18b08592b35544b05_20261110_205819.jpeg	5f8c473f81a749f18b08592b35544b05_20261110_205819.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
8	2	2027-02-09 20:23:13.983017+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-11 20:23:13.986071+05:30	uploads/f415c863fc984da292c1ca32bc540762_20261111_202313.png	f415c863fc984da292c1ca32bc540762_20261111_202313.png	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 761.8, "x_min": 190.4, "y_max": 386.9, "y_min": 146.7, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[211.6, 166.8], [370.3, 213.4], [529.0, 280.1], [719.4, 346.8], [708.9, 366.9], [507.8, 293.5], [349.1, 226.8], [201.0, 173.4]], "area_pixels": 14819.4, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 550.2}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 867.6, "x_min": 581.9, "y_max": 493.6, "y_min": 300.2, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[592.5, 320.2], [825.2, 313.5], [846.4, 466.9], [613.6, 480.2]], "area_pixels": 29638.8, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 275.1}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
9	2	2027-02-09 20:25:10.547572+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-11 20:25:10.589202+05:30	uploads/03237ae26e544fa6a9964541315ec0d2_20261111_202510.jpeg	03237ae26e544fa6a9964541315ec0d2_20261111_202510.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
10	2	2027-02-09 20:25:57.196828+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-11 20:25:57.19916+05:30	uploads/40ec7ce4df33419fa2fdd7c9b75973a9_20261111_202557.jpeg	40ec7ce4df33419fa2fdd7c9b75973a9_20261111_202557.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
11	1	2027-02-09 20:47:33.724209+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-11 20:47:33.743432+05:30	uploads/fe09739bc9ab4aabbe07b00c5950449b_20261111_204733.jpeg	fe09739bc9ab4aabbe07b00c5950449b_20261111_204733.jpeg	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 178.6, "x_min": 44.6, "y_max": 85.8, "y_min": 32.6, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[49.6, 37.0], [86.8, 47.4], [124.0, 62.2], [168.6, 77.0], [166.2, 81.4], [119.0, 65.1], [81.8, 50.3], [47.1, 38.5]], "area_pixels": 770.8, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 129.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 203.4, "x_min": 136.4, "y_max": 109.5, "y_min": 66.6, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[138.9, 71.0], [193.4, 69.6], [198.4, 103.6], [143.8, 106.6]], "area_pixels": 1541.6, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 64.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
12	1	2027-02-09 20:55:26.077996+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-11 20:55:26.085766+05:30	uploads/3d6ad575f2144bb291a6e51812fd0115_20261111_205526.png	3d6ad575f2144bb291a6e51812fd0115_20261111_205526.png	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 1981.4, "x_min": 495.4, "y_max": 890.9, "y_min": 337.9, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[550.4, 384.0], [963.2, 491.5], [1376.0, 645.1], [1871.4, 798.7], [1843.8, 844.8], [1321.0, 675.8], [908.2, 522.2], [522.9, 399.4]], "area_pixels": 88768.5, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 1431.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 2256.6, "x_min": 1513.6, "y_max": 1136.6, "y_min": 691.2, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[1541.1, 737.3], [2146.6, 721.9], [2201.6, 1075.2], [1596.2, 1105.9]], "area_pixels": 177537.0, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 715.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
13	1	2027-02-09 20:58:05.02524+05:30	0.89	HIGH PRIORITY: Perform high-pressure structural epoxy resin injection and steel plate bonding. Install wireless crack displacement telemetry sensors and re-inspect within 14 days.	2026-11-11 20:58:05.032577+05:30	uploads/cb51c5b83f5244248624185453a641d1_20261111_205805.png	cb51c5b83f5244248624185453a641d1_20261111_205805.png	Severe Damage	Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.	{"defects": [{"id": 1, "severity": "Severe Damage", "defect_type": "Longitudinal Crack", "bounding_box": {"x_max": 1981.4, "x_min": 495.4, "y_max": 890.9, "y_min": 337.9, "class_name": "longitudinal_crack", "confidence": 0.92}, "segmentation_mask": {"polygon": [[550.4, 384.0], [963.2, 491.5], [1376.0, 645.1], [1871.4, 798.7], [1843.8, 844.8], [1321.0, 675.8], [908.2, 522.2], [522.9, 399.4]], "area_pixels": 88768.5, "mask_confidence": 0.9, "estimated_width_px": 7.8, "estimated_length_px": 1431.0}}, {"id": 2, "severity": "Severe Damage", "defect_type": "Spalling", "bounding_box": {"x_max": 2256.6, "x_min": 1513.6, "y_max": 1136.6, "y_min": 691.2, "class_name": "spalling", "confidence": 0.86}, "segmentation_mask": {"polygon": [[1541.1, 737.3], [2146.6, 721.9], [2201.6, 1075.2], [1596.2, 1105.9]], "area_pixels": 177537.0, "mask_confidence": 0.88, "estimated_width_px": 14.2, "estimated_length_px": 715.5}}], "summary": "Detected 2 defect instances: longitudinal_crack, spalling with crack density 6.3%.", "total_defects": 2, "severity_level": "Severe Damage", "crack_density_percentage": 6.3}
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: infrascan_user
--

COPY public.users (id, email, hashed_password, role, created_at) FROM stdin;
3	inspector1@example.com	$2b$12$Rb4s9gSH2Z/dm5lEQK3fWeSOLTMMy4EisljHlT5pEwHk6ZDh4wlCm	INSPECTOR	2026-10-25 20:37:50.543722+05:30
4	jaiswal@gmail.com	$2b$12$5zl5Dkr87t3Rk2Sg33OmAuppyym2U0vBErRxjKbzUtHIBASOPI1zi	ADMIN	2026-10-31 13:00:24.290514+05:30
1	demo@infrascan.test	$2b$12$SXTrr8c05Z2zJI1xxghAIeCTGRtqo9YHp1lTBeb4ZWEPsCUBbn4yi	Infrastructure Inspector	2026-11-11 13:05:54.722974+05:30
2	admin@infrascan.test	$2b$12$neiKg8LLSUrV3VELUlL6i.fG5xOGejvpBH01Lyxr64VWptFVFYHjO	Administrator	2026-11-11 13:06:18.190743+05:30
\.


--
-- Name: infrastructure_assets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: infrascan_user
--

SELECT pg_catalog.setval('public.infrastructure_assets_id_seq', 2, true);


--
-- Name: inspections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: infrascan_user
--

SELECT pg_catalog.setval('public.inspections_id_seq', 2, true);


--
-- Name: predictions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: infrascan_user
--

SELECT pg_catalog.setval('public.predictions_id_seq', 13, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: infrascan_user
--

SELECT pg_catalog.setval('public.users_id_seq', 4, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: infrastructure_assets infrastructure_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.infrastructure_assets
    ADD CONSTRAINT infrastructure_assets_pkey PRIMARY KEY (id);


--
-- Name: inspections inspections_pkey; Type: CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.inspections
    ADD CONSTRAINT inspections_pkey PRIMARY KEY (id);


--
-- Name: predictions predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_infrastructure_assets_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_infrastructure_assets_id ON public.infrastructure_assets USING btree (id);


--
-- Name: ix_infrastructure_assets_name; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_infrastructure_assets_name ON public.infrastructure_assets USING btree (name);


--
-- Name: ix_infrastructure_assets_status; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_infrastructure_assets_status ON public.infrastructure_assets USING btree (status);


--
-- Name: ix_infrastructure_assets_type; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_infrastructure_assets_type ON public.infrastructure_assets USING btree (type);


--
-- Name: ix_inspections_asset_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_inspections_asset_id ON public.inspections USING btree (asset_id);


--
-- Name: ix_inspections_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_inspections_id ON public.inspections USING btree (id);


--
-- Name: ix_inspections_inspector_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_inspections_inspector_id ON public.inspections USING btree (inspector_id);


--
-- Name: ix_inspections_status; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_inspections_status ON public.inspections USING btree (status);


--
-- Name: ix_predictions_asset_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_predictions_asset_id ON public.predictions USING btree (asset_id);


--
-- Name: ix_predictions_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_predictions_id ON public.predictions USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: infrascan_user
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: inspections inspections_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.inspections
    ADD CONSTRAINT inspections_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.infrastructure_assets(id) ON DELETE CASCADE;


--
-- Name: inspections inspections_inspector_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.inspections
    ADD CONSTRAINT inspections_inspector_id_fkey FOREIGN KEY (inspector_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: predictions predictions_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infrascan_user
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.infrastructure_assets(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict S6s6L4838yUzJf6nHAufHCyDigDkpUwJyN4qCHkxYZaERcvYeWCeH8wZo97lThs

