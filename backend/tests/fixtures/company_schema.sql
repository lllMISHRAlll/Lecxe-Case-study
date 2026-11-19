--
-- PostgreSQL database dump
--


-- Dumped from database version 18.6 (Debian 18.6-1.pgdg13+2)
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: inv_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_categories (
    id character varying NOT NULL,
    name character varying NOT NULL,
    short_code character varying NOT NULL,
    "position" integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: inv_current_stock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_current_stock (
    id character varying NOT NULL,
    item_id character varying NOT NULL,
    location_id character varying NOT NULL,
    quantity double precision NOT NULL,
    min_stock_level double precision,
    max_stock_level double precision,
    last_transaction_at timestamp without time zone,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: inv_field_definitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_field_definitions (
    id character varying NOT NULL,
    name character varying NOT NULL,
    field_type character varying NOT NULL,
    required boolean NOT NULL,
    options text,
    "position" integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: inv_issued_to_targets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_issued_to_targets (
    id character varying NOT NULL,
    name character varying NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: inv_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_items (
    id character varying NOT NULL,
    item_code character varying NOT NULL,
    name character varying NOT NULL,
    category_id character varying,
    sub_category_id character varying,
    sub_category_2_id character varying,
    status character varying NOT NULL,
    unit character varying NOT NULL,
    hsn_code character varying,
    notes text,
    specifications text,
    alt_units text,
    is_spare boolean DEFAULT false NOT NULL
);


--
-- Name: inv_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_locations (
    id character varying NOT NULL,
    name character varying NOT NULL,
    address text,
    is_active boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: inv_sub_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_sub_categories (
    id character varying NOT NULL,
    name character varying NOT NULL,
    short_code character varying NOT NULL,
    category_id character varying NOT NULL,
    "position" integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: inv_sub_categories_2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_sub_categories_2 (
    id character varying NOT NULL,
    name character varying NOT NULL,
    short_code character varying NOT NULL,
    sub_category_id character varying NOT NULL,
    source_id character varying,
    standard text,
    description text,
    naming_convention text,
    convention_notes text,
    examples text,
    "position" integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    hsn_code character varying,
    nomenclature_fields text,
    nomenclature_version integer DEFAULT 1 NOT NULL,
    cut_shape character varying,
    cut_formula text
);


--
-- Name: inv_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_transactions (
    id character varying NOT NULL,
    item_id character varying NOT NULL,
    location_id character varying,
    transaction_type character varying NOT NULL,
    quantity double precision NOT NULL,
    reference_type character varying,
    reference_id character varying,
    transfer_location_id character varying,
    unit_cost double precision,
    notes text,
    created_by character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    currency character varying(3) DEFAULT 'INR'::character varying NOT NULL,
    issued_to_id character varying
);


--
-- Name: proc_po_line_regularisations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_po_line_regularisations (
    id character varying NOT NULL,
    po_id character varying NOT NULL,
    po_line_id character varying NOT NULL,
    ordered_qty numeric(14,3) NOT NULL,
    received_qty_before numeric(14,3) NOT NULL,
    regularised_qty numeric(14,3) NOT NULL,
    received_qty_after numeric(14,3) NOT NULL,
    qty_variance numeric(14,3) NOT NULL,
    unit_price numeric(14,2) NOT NULL,
    actual_amount numeric(14,2) NOT NULL,
    expected_amount numeric(14,2) NOT NULL,
    amount_variance numeric(14,2) NOT NULL,
    notes text,
    inv_transaction_id character varying,
    regularised_by character varying NOT NULL,
    regularised_at timestamp without time zone NOT NULL,
    reviewed_by character varying,
    reviewed_at timestamp without time zone,
    review_notes text
);


--
-- Name: proc_po_lines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_po_lines (
    id character varying NOT NULL,
    po_id character varying NOT NULL,
    inv_item_id character varying,
    quantity_ordered numeric(14,3) NOT NULL,
    quantity_received numeric(14,3) NOT NULL,
    unit character varying,
    unit_price numeric(14,2) NOT NULL,
    tax_percentage numeric(5,2) NOT NULL,
    line_subtotal numeric(14,2) NOT NULL,
    line_tax numeric(14,2) NOT NULL,
    line_total numeric(14,2) NOT NULL,
    notes text,
    "position" integer NOT NULL,
    custom_fields text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_regularised boolean DEFAULT false NOT NULL,
    expected_delivery_date json,
    expected_dispatch_date json
);


--
-- Name: proc_po_payment_tranches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_po_payment_tranches (
    id character varying NOT NULL,
    po_id character varying NOT NULL,
    sequence integer NOT NULL,
    stage character varying NOT NULL,
    percentage numeric(5,2) NOT NULL,
    amount numeric(14,2),
    is_advance boolean NOT NULL,
    blocks_dispatch boolean NOT NULL,
    due_basis character varying,
    due_offset_days integer,
    source character varying NOT NULL,
    cleared_at timestamp without time zone,
    cleared_by character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: proc_po_receipts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_po_receipts (
    id character varying NOT NULL,
    po_line_id character varying NOT NULL,
    quantity numeric(14,3) NOT NULL,
    location_id character varying,
    notes text,
    inv_transaction_id character varying,
    received_by character varying NOT NULL,
    received_at timestamp without time zone NOT NULL
);


--
-- Name: proc_purchase_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_purchase_orders (
    id character varying NOT NULL,
    po_number character varying NOT NULL,
    vendor_id character varying NOT NULL,
    status character varying NOT NULL,
    placed_on date,
    currency character varying NOT NULL,
    subtotal numeric(14,2) NOT NULL,
    tax_amount numeric(14,2) NOT NULL,
    total_amount numeric(14,2) NOT NULL,
    payment_terms character varying,
    delivery_location_id character varying,
    ship_to_address text,
    custom_fields text,
    created_by character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    expected_delivery_date json,
    expected_dispatch_date json
);


--
-- Name: proc_unexpected_receipt_headers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_unexpected_receipt_headers (
    id character varying NOT NULL,
    received_by character varying NOT NULL,
    received_at timestamp without time zone NOT NULL,
    notes text,
    vendor_name character varying
);


--
-- Name: proc_unexpected_receipts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_unexpected_receipts (
    id character varying NOT NULL,
    inv_item_id character varying NOT NULL,
    quantity numeric(14,3) NOT NULL,
    location_id character varying,
    notes text,
    inv_transaction_id character varying,
    received_by character varying NOT NULL,
    received_at timestamp without time zone NOT NULL,
    resolved_po_id character varying,
    resolved_by character varying,
    resolved_at timestamp without time zone,
    header_id text
);


--
-- Name: proc_vendors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proc_vendors (
    id character varying NOT NULL,
    name character varying NOT NULL,
    code character varying,
    city character varying,
    payment_terms character varying,
    is_active boolean NOT NULL,
    created_by character varying NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: inv_categories inv_categories_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_categories
    ADD CONSTRAINT inv_categories_name_key UNIQUE (name);


--
-- Name: inv_categories inv_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_categories
    ADD CONSTRAINT inv_categories_pkey PRIMARY KEY (id);


--
-- Name: inv_categories inv_categories_short_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_categories
    ADD CONSTRAINT inv_categories_short_code_key UNIQUE (short_code);


--
-- Name: inv_current_stock inv_current_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_current_stock
    ADD CONSTRAINT inv_current_stock_pkey PRIMARY KEY (id);


--
-- Name: inv_field_definitions inv_field_definitions_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_field_definitions
    ADD CONSTRAINT inv_field_definitions_name_key UNIQUE (name);


--
-- Name: inv_field_definitions inv_field_definitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_field_definitions
    ADD CONSTRAINT inv_field_definitions_pkey PRIMARY KEY (id);


--
-- Name: inv_issued_to_targets inv_issued_to_targets_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_issued_to_targets
    ADD CONSTRAINT inv_issued_to_targets_name_key UNIQUE (name);


--
-- Name: inv_issued_to_targets inv_issued_to_targets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_issued_to_targets
    ADD CONSTRAINT inv_issued_to_targets_pkey PRIMARY KEY (id);


--
-- Name: inv_items inv_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_items
    ADD CONSTRAINT inv_items_pkey PRIMARY KEY (id);


--
-- Name: inv_locations inv_locations_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_locations
    ADD CONSTRAINT inv_locations_name_key UNIQUE (name);


--
-- Name: inv_locations inv_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_locations
    ADD CONSTRAINT inv_locations_pkey PRIMARY KEY (id);


--
-- Name: inv_sub_categories_2 inv_sub_categories_2_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories_2
    ADD CONSTRAINT inv_sub_categories_2_pkey PRIMARY KEY (id);


--
-- Name: inv_sub_categories inv_sub_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories
    ADD CONSTRAINT inv_sub_categories_pkey PRIMARY KEY (id);


--
-- Name: inv_transactions inv_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_transactions
    ADD CONSTRAINT inv_transactions_pkey PRIMARY KEY (id);


--
-- Name: proc_po_line_regularisations proc_po_line_regularisations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_line_regularisations
    ADD CONSTRAINT proc_po_line_regularisations_pkey PRIMARY KEY (id);


--
-- Name: proc_po_lines proc_po_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_lines
    ADD CONSTRAINT proc_po_lines_pkey PRIMARY KEY (id);


--
-- Name: proc_po_payment_tranches proc_po_payment_tranches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_payment_tranches
    ADD CONSTRAINT proc_po_payment_tranches_pkey PRIMARY KEY (id);


--
-- Name: proc_po_receipts proc_po_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_receipts
    ADD CONSTRAINT proc_po_receipts_pkey PRIMARY KEY (id);


--
-- Name: proc_purchase_orders proc_purchase_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_purchase_orders
    ADD CONSTRAINT proc_purchase_orders_pkey PRIMARY KEY (id);


--
-- Name: proc_unexpected_receipt_headers proc_unexpected_receipt_headers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_unexpected_receipt_headers
    ADD CONSTRAINT proc_unexpected_receipt_headers_pkey PRIMARY KEY (id);


--
-- Name: proc_unexpected_receipts proc_unexpected_receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_unexpected_receipts
    ADD CONSTRAINT proc_unexpected_receipts_pkey PRIMARY KEY (id);


--
-- Name: proc_vendors proc_vendors_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_vendors
    ADD CONSTRAINT proc_vendors_code_key UNIQUE (code);


--
-- Name: proc_vendors proc_vendors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_vendors
    ADD CONSTRAINT proc_vendors_pkey PRIMARY KEY (id);


--
-- Name: inv_current_stock uq_inv_stock_item_location; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_current_stock
    ADD CONSTRAINT uq_inv_stock_item_location UNIQUE (item_id, location_id);


--
-- Name: inv_sub_categories_2 uq_inv_sub_category_2_sub_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories_2
    ADD CONSTRAINT uq_inv_sub_category_2_sub_code UNIQUE (sub_category_id, short_code);


--
-- Name: inv_sub_categories_2 uq_inv_sub_category_2_sub_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories_2
    ADD CONSTRAINT uq_inv_sub_category_2_sub_name UNIQUE (sub_category_id, name);


--
-- Name: inv_sub_categories uq_inv_sub_category_cat_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories
    ADD CONSTRAINT uq_inv_sub_category_cat_code UNIQUE (category_id, short_code);


--
-- Name: inv_sub_categories uq_inv_sub_category_cat_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories
    ADD CONSTRAINT uq_inv_sub_category_cat_name UNIQUE (category_id, name);


--
-- Name: ix_inv_current_stock_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_current_stock_item_id ON public.inv_current_stock USING btree (item_id);


--
-- Name: ix_inv_current_stock_location_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_current_stock_location_id ON public.inv_current_stock USING btree (location_id);


--
-- Name: ix_inv_items_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_items_category_id ON public.inv_items USING btree (category_id);


--
-- Name: ix_inv_items_is_spare; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_items_is_spare ON public.inv_items USING btree (is_spare);


--
-- Name: ix_inv_items_item_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_inv_items_item_code ON public.inv_items USING btree (item_code);


--
-- Name: ix_inv_items_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_inv_items_name ON public.inv_items USING btree (name);


--
-- Name: ix_inv_items_sub_category_2_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_items_sub_category_2_id ON public.inv_items USING btree (sub_category_2_id);


--
-- Name: ix_inv_items_sub_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_items_sub_category_id ON public.inv_items USING btree (sub_category_id);


--
-- Name: ix_inv_sub_categories_2_sub_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_sub_categories_2_sub_category_id ON public.inv_sub_categories_2 USING btree (sub_category_id);


--
-- Name: ix_inv_sub_categories_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_sub_categories_category_id ON public.inv_sub_categories USING btree (category_id);


--
-- Name: ix_inv_transactions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_transactions_created_at ON public.inv_transactions USING btree (created_at);


--
-- Name: ix_inv_transactions_issued_to_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_transactions_issued_to_id ON public.inv_transactions USING btree (issued_to_id);


--
-- Name: ix_inv_transactions_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_transactions_item_id ON public.inv_transactions USING btree (item_id);


--
-- Name: ix_inv_transactions_location_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_transactions_location_id ON public.inv_transactions USING btree (location_id);


--
-- Name: ix_inv_transactions_reference_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inv_transactions_reference_id ON public.inv_transactions USING btree (reference_id);


--
-- Name: ix_proc_po_line_regularisations_inv_transaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_line_regularisations_inv_transaction_id ON public.proc_po_line_regularisations USING btree (inv_transaction_id);


--
-- Name: ix_proc_po_line_regularisations_po_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_line_regularisations_po_id ON public.proc_po_line_regularisations USING btree (po_id);


--
-- Name: ix_proc_po_line_regularisations_po_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_line_regularisations_po_line_id ON public.proc_po_line_regularisations USING btree (po_line_id);


--
-- Name: ix_proc_po_line_regularisations_regularised_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_line_regularisations_regularised_at ON public.proc_po_line_regularisations USING btree (regularised_at);


--
-- Name: ix_proc_po_lines_inv_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_lines_inv_item_id ON public.proc_po_lines USING btree (inv_item_id);


--
-- Name: ix_proc_po_lines_is_regularised; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_lines_is_regularised ON public.proc_po_lines USING btree (is_regularised);


--
-- Name: ix_proc_po_lines_po_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_lines_po_id ON public.proc_po_lines USING btree (po_id);


--
-- Name: ix_proc_po_payment_tranches_blocks_dispatch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_payment_tranches_blocks_dispatch ON public.proc_po_payment_tranches USING btree (blocks_dispatch);


--
-- Name: ix_proc_po_payment_tranches_cleared_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_payment_tranches_cleared_at ON public.proc_po_payment_tranches USING btree (cleared_at);


--
-- Name: ix_proc_po_payment_tranches_is_advance; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_payment_tranches_is_advance ON public.proc_po_payment_tranches USING btree (is_advance);


--
-- Name: ix_proc_po_payment_tranches_po_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_payment_tranches_po_id ON public.proc_po_payment_tranches USING btree (po_id);


--
-- Name: ix_proc_po_payment_tranches_po_id_sequence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_payment_tranches_po_id_sequence ON public.proc_po_payment_tranches USING btree (po_id, sequence);


--
-- Name: ix_proc_po_receipts_inv_transaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_receipts_inv_transaction_id ON public.proc_po_receipts USING btree (inv_transaction_id);


--
-- Name: ix_proc_po_receipts_po_line_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_receipts_po_line_id ON public.proc_po_receipts USING btree (po_line_id);


--
-- Name: ix_proc_po_receipts_received_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_po_receipts_received_at ON public.proc_po_receipts USING btree (received_at);


--
-- Name: ix_proc_purchase_orders_placed_on; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_purchase_orders_placed_on ON public.proc_purchase_orders USING btree (placed_on);


--
-- Name: ix_proc_purchase_orders_po_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_proc_purchase_orders_po_number ON public.proc_purchase_orders USING btree (po_number);


--
-- Name: ix_proc_purchase_orders_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_purchase_orders_status ON public.proc_purchase_orders USING btree (status);


--
-- Name: ix_proc_purchase_orders_vendor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_purchase_orders_vendor_id ON public.proc_purchase_orders USING btree (vendor_id);


--
-- Name: ix_proc_unexpected_receipt_headers_received_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_unexpected_receipt_headers_received_at ON public.proc_unexpected_receipt_headers USING btree (received_at);


--
-- Name: ix_proc_unexpected_receipts_inv_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_unexpected_receipts_inv_item_id ON public.proc_unexpected_receipts USING btree (inv_item_id);


--
-- Name: ix_proc_unexpected_receipts_inv_transaction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_unexpected_receipts_inv_transaction_id ON public.proc_unexpected_receipts USING btree (inv_transaction_id);


--
-- Name: ix_proc_unexpected_receipts_received_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_unexpected_receipts_received_at ON public.proc_unexpected_receipts USING btree (received_at);


--
-- Name: ix_proc_unexpected_receipts_resolved_po_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_unexpected_receipts_resolved_po_id ON public.proc_unexpected_receipts USING btree (resolved_po_id);


--
-- Name: ix_proc_vendors_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_proc_vendors_name ON public.proc_vendors USING btree (name);


--
-- Name: inv_current_stock inv_current_stock_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_current_stock
    ADD CONSTRAINT inv_current_stock_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.inv_locations(id) ON DELETE CASCADE;


--
-- Name: inv_items inv_items_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_items
    ADD CONSTRAINT inv_items_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.inv_categories(id) ON DELETE SET NULL;


--
-- Name: inv_items inv_items_sub_category_2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_items
    ADD CONSTRAINT inv_items_sub_category_2_id_fkey FOREIGN KEY (sub_category_2_id) REFERENCES public.inv_sub_categories_2(id) ON DELETE SET NULL;


--
-- Name: inv_items inv_items_sub_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_items
    ADD CONSTRAINT inv_items_sub_category_id_fkey FOREIGN KEY (sub_category_id) REFERENCES public.inv_sub_categories(id) ON DELETE SET NULL;


--
-- Name: inv_sub_categories_2 inv_sub_categories_2_sub_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories_2
    ADD CONSTRAINT inv_sub_categories_2_sub_category_id_fkey FOREIGN KEY (sub_category_id) REFERENCES public.inv_sub_categories(id) ON DELETE RESTRICT;


--
-- Name: inv_sub_categories inv_sub_categories_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_sub_categories
    ADD CONSTRAINT inv_sub_categories_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.inv_categories(id) ON DELETE RESTRICT;


--
-- Name: inv_transactions inv_transactions_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_transactions
    ADD CONSTRAINT inv_transactions_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.inv_locations(id) ON DELETE RESTRICT;


--
-- Name: proc_po_line_regularisations proc_po_line_regularisations_po_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_line_regularisations
    ADD CONSTRAINT proc_po_line_regularisations_po_id_fkey FOREIGN KEY (po_id) REFERENCES public.proc_purchase_orders(id) ON DELETE CASCADE;


--
-- Name: proc_po_line_regularisations proc_po_line_regularisations_po_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_line_regularisations
    ADD CONSTRAINT proc_po_line_regularisations_po_line_id_fkey FOREIGN KEY (po_line_id) REFERENCES public.proc_po_lines(id) ON DELETE CASCADE;


--
-- Name: proc_po_lines proc_po_lines_po_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_lines
    ADD CONSTRAINT proc_po_lines_po_id_fkey FOREIGN KEY (po_id) REFERENCES public.proc_purchase_orders(id) ON DELETE CASCADE;


--
-- Name: proc_po_receipts proc_po_receipts_po_line_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_po_receipts
    ADD CONSTRAINT proc_po_receipts_po_line_id_fkey FOREIGN KEY (po_line_id) REFERENCES public.proc_po_lines(id) ON DELETE CASCADE;


--
-- Name: proc_purchase_orders proc_purchase_orders_vendor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_purchase_orders
    ADD CONSTRAINT proc_purchase_orders_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES public.proc_vendors(id) ON DELETE RESTRICT;


--
-- Name: proc_unexpected_receipts proc_unexpected_receipts_header_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_unexpected_receipts
    ADD CONSTRAINT proc_unexpected_receipts_header_id_fkey FOREIGN KEY (header_id) REFERENCES public.proc_unexpected_receipt_headers(id) ON DELETE CASCADE;


--
-- Name: proc_unexpected_receipts proc_unexpected_receipts_resolved_po_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proc_unexpected_receipts
    ADD CONSTRAINT proc_unexpected_receipts_resolved_po_id_fkey FOREIGN KEY (resolved_po_id) REFERENCES public.proc_purchase_orders(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--


