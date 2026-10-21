import src.config
from src.pipeline.extraction.factory import get_extraction_strategy
from src.pipeline.transformations import apply_transformation
from src.pipeline.aggregations import apply_aggregation
import streamlit as st
import plotly.express as px


def main():
    @st.cache_data
    def load_data():
        strategy = get_extraction_strategy()
        extracted_files = strategy.extract_raw_files()
        apply_transformation(extracted_files)
        df_daily_revenue = apply_aggregation(extracted_files, "compute_daily_revenue")
        df_amount_unique_users = apply_aggregation(extracted_files, "find_amount_of_unique_users")
        df_unique_sets_of_authors = apply_aggregation(extracted_files, "find_unique_sets_of_authors")
        df_most_popular_author = apply_aggregation(extracted_files, "most_popular_author")
        df_top_customer_by_spending = apply_aggregation(extracted_files, "top_customer_by_spending")
        return (
            extracted_files,
            df_daily_revenue,
            df_amount_unique_users,
            df_unique_sets_of_authors,
            df_most_popular_author,
            df_top_customer_by_spending
        )


    def load_dashboard(
            extracted_files,
            df_daily_revenue, 
            df_amount_unique_users, 
            df_unique_sets_of_authors, 
            df_most_popular_author, 
            df_top_customer_by_spending
            ):
        st.sidebar.title("Navigation & Filters")
        available_stores = [store for store in extracted_files.keys()]
        selected_store = st.sidebar.selectbox("Select a store", available_stores)

        st.title(f"{selected_store} Executive Summary")
        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["Financial Performance", "User Analytics", "Author Insights"])

        with tab1:
            st.subheader("Revenue Overview")
            fig = px.line(
                df_daily_revenue[selected_store],
                x="date",
                y="paid_price",
                markers=True
                )
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Top 5 Revenue Days")
            top_5_days = df_daily_revenue[selected_store].nlargest(5, "paid_price")
            st.dataframe(top_5_days, use_container_width=True, hide_index=True)

        with tab2:
            col1, col2 = st.columns([1, 2])
            with col1:
                unique_users_count = df_amount_unique_users[selected_store]
                st.metric(label="Total Unique Users", value=f"{unique_users_count}")
            with col2:
                st.subheader("Top Spending Customer")
                top_buyer_aliases = df_top_customer_by_spending[selected_store]["user_names"]
                if len(top_buyer_aliases) > 0:
                    top_buyer_aliases = top_buyer_aliases[0] if isinstance(top_buyer_aliases[0], list) else top_buyer_aliases
                else:
                    top_buyer_aliases = []
                st.markdown("Aliases")
                st.write(f"`{'`, `'.join(top_buyer_aliases)}`")

        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                unique_author_sets = df_unique_sets_of_authors[selected_store]
                st.metric(label="Unique Author Collections / Sets", value=unique_author_sets)
            with col2:
                st.subheader("Most Popular Authors")
                most_popular_authors = df_most_popular_author[selected_store]
                st.metric(label="Most Popular author name/s", value=most_popular_authors)


    st.set_page_config(
        page_title="Store Performance Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )


    data_packages = load_data()
    load_dashboard(*data_packages)


if __name__ == "__main__":
    main()